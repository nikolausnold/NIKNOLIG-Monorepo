package org.niknolig.devicelink

import java.util.Base64

/** Persistent client state. Implementations must keep tokens encrypted at rest. */
interface LinkStateStore {
    fun deviceId(): String?
    fun saveDeviceId(id: String)
    fun session(): DeviceSession?
    fun saveSession(session: DeviceSession)
    fun clearSession()
    fun clear()
}

data class PeerDevice(val id: String, val appArea: String, val displayName: String, val fingerprint: String)

data class PairingOffer(val pairingId: String, val code: String, val expiresAt: String)

data class PairingState(
    val pairingId: String,
    val state: String,
    val role: String,
    val expiresAt: String,
    val peer: PeerDevice?,
    val confirmedByMe: Boolean,
    val confirmedByPeer: Boolean,
    val linkId: String?,
    val shortAuthString: String?,
)

data class LinkInfo(val linkId: String, val state: String, val expiresAt: String, val peer: PeerDevice)

data class GrantInfo(val grantId: String, val linkId: String, val scope: String, val direction: String, val expiresAt: String)

data class StatusInfo(val state: String, val detail: String?, val reportedAt: String?)

data class PeerEvent(val kind: String, val detail: String?, val createdAt: String?)

object DeviceLinkScopes {
    const val STATUS_READ = "status:read"
    const val EVENTS_READ = "events:read"
    const val ALERTS_SEND = "alerts:send"
}

/**
 * Authenticated operations on top of the device protocol. Sessions rotate and are persisted after each
 * refresh; one 401 triggers a refresh and, if that fails, a fresh challenge session before the call is retried.
 */
class DeviceLinkService(
    private val gate: DeviceLinkGate,
    private val transport: DeviceLinkTransport,
    private val signer: DeviceSigner,
    private val store: LinkStateStore,
) {
    private val client = DeviceLinkClient(gate, transport, signer)

    val isRegistered: Boolean get() = store.deviceId() != null

    /** [userToken] is the account JWT; it is used once and never stored. */
    fun register(userToken: String, area: String, installationId: String, displayName: String): String {
        gate.require()
        val principal = JwtSubject.of(userToken)
        val id = client.register(userToken, area, installationId, principal, displayName)
        store.saveDeviceId(id)
        store.saveSession(client.openSession(id))
        return id
    }

    fun createPairing(): PairingOffer = call("POST", "/v1/pairings", null, 201).let {
        PairingOffer(it.str("pairingId"), it.str("code"), it.str("expiresAt"))
    }

    fun claimPairing(code: String): PairingState =
        call("POST", "/v1/pairings/claim", mapOf("code" to code), 200).toPairing()

    fun pairing(pairingId: String): PairingState =
        call("GET", "/v1/pairings/${segment(pairingId)}", null, 200).toPairing()

    fun confirmPairing(pairingId: String): PairingState =
        call("POST", "/v1/pairings/${segment(pairingId)}/confirm", null, 200).toPairing()

    fun cancelPairing(pairingId: String) {
        call("POST", "/v1/pairings/${segment(pairingId)}/cancel", null, 200)
    }

    fun links(): List<LinkInfo> = call("GET", "/v1/links", null, 200).list("links").map {
        LinkInfo(it.str("linkId"), it.str("state"), it.str("expiresAt"), it.obj("peer")!!.toPeer())
    }

    fun revokeLink(linkId: String) {
        call("DELETE", "/v1/links/${segment(linkId)}", null, 200)
    }

    fun grants(linkId: String): List<GrantInfo> =
        call("GET", "/v1/links/${segment(linkId)}/grants", null, 200).list("grants").map { it.toGrant() }

    fun createGrant(linkId: String, scope: String, ttlSeconds: Long): GrantInfo =
        call("POST", "/v1/links/${segment(linkId)}/grants", mapOf("scope" to scope, "ttlSeconds" to ttlSeconds), 201)
            .toGrant()

    fun revokeGrant(grantId: String) {
        call("DELETE", "/v1/grants/${segment(grantId)}", null, 200)
    }

    fun reportStatus(state: String, detail: String?) {
        call("PUT", "/v1/status", mapOf("state" to state, "detail" to detail), 200)
    }

    fun peerStatus(linkId: String): StatusInfo =
        call("GET", "/v1/links/${segment(linkId)}/peer/status", null, 200).toStatus()

    fun peerEvents(linkId: String, limit: Int = 20): List<PeerEvent> =
        call("GET", "/v1/links/${segment(linkId)}/peer/events?limit=$limit", null, 200).list("events").map {
            PeerEvent(it.str("kind"), it["detail"] as? String, it["createdAt"] as? String)
        }

    fun sendAlert(linkId: String, kind: String, detail: String?) {
        call("POST", "/v1/events", mapOf("kind" to kind, "detail" to detail, "linkId" to linkId), 201)
    }

    /** Revokes this device on the server (all links and sessions), then forgets local state. */
    fun revokeThisDevice() {
        val id = store.deviceId() ?: return
        call("DELETE", "/v1/devices/${segment(id)}", null, 200)
        store.clear()
    }

    /** Ends only this session; the device identity stays registered. */
    fun signOut() {
        if (store.session() == null) return
        try {
            call("DELETE", "/v1/sessions/current", null, 200)
        } finally {
            store.clearSession()
        }
    }

    private fun call(method: String, path: String, body: Map<String, Any?>?, expected: Int): Map<String, Any?> {
        gate.require()
        val deviceId = store.deviceId() ?: throw DeviceLinkNotRegisteredException()
        var session = store.session() ?: synchronized(sessionRenewLock) { store.session() ?: openSession(deviceId) }
        var response = transport.request(method, path, session.accessToken, body)
        if (response.status == 401) {
            session = renew(deviceId, session)
            response = transport.request(method, path, session.accessToken, body)
        }
        if (response.status != expected) throw DeviceLinkException(response.status, expected, path.substringBefore('?'))
        return response.body
    }

    /**
     * Callers share one stored session. Renewal is serialized and re-reads the store: if another caller already
     * rotated the tokens, those are used instead of replaying the consumed refresh token (which would revoke them).
     */
    private fun renew(deviceId: String, stale: DeviceSession): DeviceSession = synchronized(sessionRenewLock) {
        val current = store.session()
        if (current != null && current != stale) return current
        val renewed = try {
            client.refresh(stale)
        } catch (error: DeviceLinkException) {
            if (error.statusCode != 401) throw error
            openSession(deviceId)
        }
        store.saveSession(renewed)
        renewed
    }

    private companion object {
        // A process-wide lock also covers overlapping Activity/service instances sharing the same store.
        val sessionRenewLock = Any()
    }

    private fun openSession(deviceId: String): DeviceSession =
        client.openSession(deviceId).also { store.saveSession(it) }

    private fun segment(value: String): String {
        require(value.isNotEmpty() && value.all { it.isLetterOrDigit() || it == '-' }) { "Invalid identifier" }
        return value
    }

    private fun Map<String, Any?>.str(key: String): String =
        this[key] as? String ?: throw DeviceLinkProtocolException(200, key)

    @Suppress("UNCHECKED_CAST")
    private fun Map<String, Any?>.obj(key: String): Map<String, Any?>? = this[key] as? Map<String, Any?>

    @Suppress("UNCHECKED_CAST")
    private fun Map<String, Any?>.list(key: String): List<Map<String, Any?>> =
        (this[key] as? List<*>)?.map { it as? Map<String, Any?> ?: throw DeviceLinkProtocolException(200, key) }
            ?: throw DeviceLinkProtocolException(200, key)

    private fun Map<String, Any?>.toPeer() =
        PeerDevice(str("id"), str("appArea"), str("displayName"), str("fingerprint"))

    private fun Map<String, Any?>.toGrant() =
        GrantInfo(str("grantId"), str("linkId"), str("scope"), str("direction"), str("expiresAt"))

    private fun Map<String, Any?>.toStatus() =
        StatusInfo(str("state"), this["detail"] as? String, this["reportedAt"] as? String)

    private fun Map<String, Any?>.toPairing() = PairingState(
        pairingId = str("pairingId"),
        state = str("state"),
        role = str("role"),
        expiresAt = str("expiresAt"),
        peer = obj("peer")?.toPeer(),
        confirmedByMe = this["confirmedByMe"] == true,
        confirmedByPeer = this["confirmedByPeer"] == true,
        linkId = this["linkId"] as? String,
        shortAuthString = this["shortAuthString"] as? String,
    )
}

/** Owner-account recovery for a registered device whose device-authenticated session was revoked. */
class DeviceLinkRecovery(
    private val gate: DeviceLinkGate,
    private val transport: DeviceLinkTransport,
    private val store: LinkStateStore,
) {
    /**
     * Confirms revocation through the owner-JWT endpoint before clearing the local identity.
     * [clearDeviceKey] must remove platform key material and key-mode metadata.
     */
    fun recoverRevokedDevice(userToken: String, clearDeviceKey: () -> Unit) {
        gate.require()
        val deviceId = store.deviceId() ?: throw DeviceLinkNotRegisteredException()
        val path = "/v1/devices/${segment(deviceId)}"
        val response = transport.request("DELETE", path, userToken, null)
        if (response.status != 200) throw DeviceLinkException(response.status, 200, path)
        clearDeviceKey()
        store.clear()
    }

    private fun segment(value: String): String {
        require(value.isNotEmpty() && value.all { it.isLetterOrDigit() || it == '-' }) { "Invalid identifier" }
        return value
    }
}

class DeviceLinkNotRegisteredException : IllegalStateException("This device is not registered.")

/** Reads the `sub` claim only to build the registration proof; the backend verifies the full JWT. */
object JwtSubject {
    fun of(token: String): String {
        val parts = token.split('.')
        require(parts.size == 3) { "Malformed account token" }
        val payload = Json.decodeObject(String(Base64.getUrlDecoder().decode(parts[1]), Charsets.UTF_8))
        val subject = payload["sub"] as? String
        require(!subject.isNullOrBlank()) { "Account token has no subject" }
        return subject
    }
}

class AppAreaClaimException(val reason: Reason) : IllegalStateException("Account token has no usable app_area claim.") {
    enum class Reason { MISSING, MISMATCH, EXPIRED }
}

/**
 * Pre-flight check of the `app_metadata.app_area` claim. The backend remains the authority and verifies the
 * token signature; this only turns a certain server-side 401/403 into an understandable local error.
 */
object AppAreaClaim {
    fun require(token: String, expectedArea: String, nowEpochSeconds: Long) {
        val parts = token.split('.')
        require(parts.size == 3) { "Malformed account token" }
        val payload = Json.decodeObject(String(Base64.getUrlDecoder().decode(parts[1]), Charsets.UTF_8))
        (payload["exp"] as? Number)?.let {
            if (it.toLong() <= nowEpochSeconds) throw AppAreaClaimException(AppAreaClaimException.Reason.EXPIRED)
        }
        val metadata = payload["app_metadata"] as? Map<*, *>
        val area = metadata?.get("app_area") as? String
            ?: throw AppAreaClaimException(AppAreaClaimException.Reason.MISSING)
        if (area != expectedArea) throw AppAreaClaimException(AppAreaClaimException.Reason.MISMATCH)
    }
}

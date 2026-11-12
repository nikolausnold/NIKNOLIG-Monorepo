package org.niknolig.devicelink

import java.util.Base64

/** Feature gate. Stays closed until the written SecurityChain-P0 approval exists. */
class DeviceLinkGate(private val p0Approved: Boolean = false) {
    val isOpen: Boolean get() = p0Approved

    fun require() {
        if (!p0Approved) throw DeviceLinkBlockedException()
    }
}

class DeviceLinkBlockedException :
    IllegalStateException("Device link is disabled; enable it only after the required security approval.")

class DeviceLinkException(
    val statusCode: Int,
    val expectedStatusCode: Int,
    val path: String,
) : RuntimeException(
    "Device link request failed for $path (expected HTTP $expectedStatusCode, received HTTP $statusCode).",
)

class DeviceLinkProtocolException(val statusCode: Int, val field: String) :
    RuntimeException("Device link response is missing '$field' (HTTP $statusCode).")

/** Device key abstraction; Android implementations must use a non-exportable Keystore key. */
interface DeviceSigner {
    /** Raw 32-byte Ed25519 public key. */
    val publicKey: ByteArray

    /** Raw 64-byte Ed25519 signature. */
    fun sign(message: ByteArray): ByteArray
}

data class TransportResponse(val status: Int, val body: Map<String, Any?>)

/** Transport failure before any HTTP response was received (offline, DNS, TLS, timeout). */
class DeviceLinkNetworkException(val timedOut: Boolean, cause: Throwable? = null) :
    RuntimeException(if (timedOut) "Device link request timed out." else "Device link network error.", cause)

interface DeviceLinkTransport {
    /** Implementations must throw [DeviceLinkNetworkException] for failures without an HTTP response. */
    fun request(method: String, path: String, bearer: String?, body: Map<String, Any?>?): TransportResponse
}

data class DeviceSession(val accessToken: String, val refreshToken: String)

object DeviceProtocol {
    fun b64url(data: ByteArray): String = Base64.getUrlEncoder().withoutPadding().encodeToString(data)

    fun registrationMessage(area: String, installationId: String, principal: String): ByteArray =
        listOf("niknolig-device-register-v1", area, installationId, principal)
            .joinToString("\n").toByteArray(Charsets.UTF_8)

    fun sessionMessage(deviceId: String, nonce: String): ByteArray =
        listOf("niknolig-device-session-v1", deviceId, nonce)
            .joinToString("\n").toByteArray(Charsets.UTF_8)
}

class DeviceLinkClient(
    private val gate: DeviceLinkGate,
    private val transport: DeviceLinkTransport,
    private val signer: DeviceSigner,
) {
    /** [area] is the backend app-area string, [principal] the verified user id. */
    fun register(
        userToken: String,
        area: String,
        installationId: String,
        principal: String,
        displayName: String,
    ): String {
        gate.require()
        val proof = signer.sign(DeviceProtocol.registrationMessage(area, installationId, principal))
        val response = transport.request(
            "POST",
            "/v1/devices",
            userToken,
            mapOf(
                "installationId" to installationId,
                "publicKey" to DeviceProtocol.b64url(signer.publicKey),
                "proof" to DeviceProtocol.b64url(proof),
                "displayName" to displayName,
            ),
        )
        return response.expect(201, "/v1/devices").body["id"] as? String
            ?: throw DeviceLinkProtocolException(response.status, "id")
    }

    fun openSession(deviceId: String): DeviceSession {
        gate.require()
        val challengePath = "/v1/devices/$deviceId/challenge"
        val challenge = transport.request("POST", challengePath, null, emptyMap()).expect(200, challengePath)
        val nonce = challenge.body["nonce"] as? String ?: throw DeviceLinkProtocolException(challenge.status, "nonce")
        val signature = signer.sign(DeviceProtocol.sessionMessage(deviceId, nonce))
        return transport.request(
            "POST",
            "/v1/devices/$deviceId/session",
            null,
            mapOf("nonce" to nonce, "signature" to DeviceProtocol.b64url(signature)),
        ).expect(201, "/v1/devices/$deviceId/session").toSession()
    }

    /** Refresh tokens rotate; callers must persist the returned pair and discard the old one. */
    fun refresh(session: DeviceSession): DeviceSession {
        gate.require()
        return transport.request("POST", "/v1/sessions/refresh", null, mapOf("refreshToken" to session.refreshToken))
            .expect(200, "/v1/sessions/refresh").toSession()
    }

    private fun TransportResponse.expect(code: Int, path: String): TransportResponse {
        if (status != code) throw DeviceLinkException(status, code, path)
        return this
    }

    private fun TransportResponse.toSession(): DeviceSession = DeviceSession(
        accessToken = body["accessToken"] as? String ?: throw DeviceLinkProtocolException(status, "accessToken"),
        refreshToken = body["refreshToken"] as? String ?: throw DeviceLinkProtocolException(status, "refreshToken"),
    )
}

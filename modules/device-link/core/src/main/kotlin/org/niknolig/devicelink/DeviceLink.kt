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
    IllegalStateException("Device link is blocked until SecurityChain-P0 is approved.")

class DeviceLinkException(val statusCode: Int) : RuntimeException("Device link request failed ($statusCode).")

class DeviceLinkProtocolException(val statusCode: Int, val field: String) :
    RuntimeException("Device link response is missing '$field' (HTTP $statusCode).")

/** Device key abstraction; Android implementations must use a non-exportable Keystore key. */
interface DeviceSigner {
    /** Raw 32-byte Ed25519 public key. */
    val publicKey: ByteArray

    /** Raw 64-byte Ed25519 signature. */
    fun sign(message: ByteArray): ByteArray
}

data class TransportResponse(val status: Int, val body: Map<String, String>)

interface DeviceLinkTransport {
    fun post(path: String, bearer: String?, body: Map<String, String>): TransportResponse
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
        val response = transport.post(
            "/v1/devices",
            userToken,
            mapOf(
                "installationId" to installationId,
                "publicKey" to DeviceProtocol.b64url(signer.publicKey),
                "proof" to DeviceProtocol.b64url(proof),
                "displayName" to displayName,
            ),
        )
        return response.expect(201).body["id"]
            ?: throw DeviceLinkProtocolException(response.status, "id")
    }

    fun openSession(deviceId: String): DeviceSession {
        gate.require()
        val challenge = transport.post("/v1/devices/$deviceId/challenge", null, emptyMap()).expect(200)
        val nonce = challenge.body["nonce"] ?: throw DeviceLinkProtocolException(challenge.status, "nonce")
        val signature = signer.sign(DeviceProtocol.sessionMessage(deviceId, nonce))
        return transport.post(
            "/v1/devices/$deviceId/session",
            null,
            mapOf("nonce" to nonce, "signature" to DeviceProtocol.b64url(signature)),
        ).expect(201).toSession()
    }

    /** Refresh tokens rotate; callers must persist the returned pair and discard the old one. */
    fun refresh(session: DeviceSession): DeviceSession {
        gate.require()
        return transport.post("/v1/sessions/refresh", null, mapOf("refreshToken" to session.refreshToken))
            .expect(200).toSession()
    }

    private fun TransportResponse.expect(code: Int): TransportResponse {
        if (status != code) throw DeviceLinkException(status)
        return this
    }

    private fun TransportResponse.toSession(): DeviceSession = DeviceSession(
        accessToken = body["accessToken"] ?: throw DeviceLinkProtocolException(status, "accessToken"),
        refreshToken = body["refreshToken"] ?: throw DeviceLinkProtocolException(status, "refreshToken"),
    )
}

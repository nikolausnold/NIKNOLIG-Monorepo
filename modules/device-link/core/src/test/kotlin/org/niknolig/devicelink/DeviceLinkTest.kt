package org.niknolig.devicelink

import java.security.KeyPairGenerator
import java.security.Signature
import java.security.interfaces.EdECPublicKey
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

class DeviceLinkTest {
    private val keyPair = KeyPairGenerator.getInstance("Ed25519").generateKeyPair()
    private val signer = object : DeviceSigner {
        override val publicKey: ByteArray = rawEd25519PublicKey(keyPair.public as EdECPublicKey)
        override fun sign(message: ByteArray): ByteArray =
            Signature.getInstance("Ed25519").run {
                initSign(keyPair.private); update(message); sign()
            }
    }

    private class Recorder(val replies: ArrayDeque<TransportResponse>) : DeviceLinkTransport {
        val calls = mutableListOf<Triple<String, String?, Map<String, String>>>()
        override fun post(path: String, bearer: String?, body: Map<String, String>): TransportResponse {
            calls += Triple(path, bearer, body)
            return replies.removeFirst()
        }
    }

    @Test
    fun closedGateBlocksEverythingWithoutNetwork() {
        val transport = Recorder(ArrayDeque())
        val client = DeviceLinkClient(DeviceLinkGate(), transport, signer)
        try {
            client.openSession("id"); fail()
        } catch (_: DeviceLinkBlockedException) {
        }
        try {
            client.register("t", "a", "i", "p", "n"); fail()
        } catch (_: DeviceLinkBlockedException) {
        }
        assertTrue(transport.calls.isEmpty())
    }

    @Test
    fun sessionSignatureVerifiesOverProtocolMessage() {
        val nonce = DeviceProtocol.b64url(ByteArray(32) { it.toByte() })
        val transport = Recorder(
            ArrayDeque(
                listOf(
                    TransportResponse(200, mapOf("nonce" to nonce)),
                    TransportResponse(201, mapOf("accessToken" to "a", "refreshToken" to "r")),
                ),
            ),
        )
        val session = DeviceLinkClient(DeviceLinkGate(true), transport, signer).openSession("dev")
        assertEquals(DeviceSession("a", "r"), session)
        val sent = java.util.Base64.getUrlDecoder().decode(transport.calls[1].third.getValue("signature"))
        assertEquals(64, sent.size)
        val verifier = Signature.getInstance("Ed25519").apply {
            initVerify(keyPair.public)
            update("niknolig-device-session-v1\ndev\n$nonce".toByteArray(Charsets.UTF_8))
        }
        assertTrue(verifier.verify(sent))
    }

    @Test
    fun registerSendsProofAndMapsErrors() {
        val ok = Recorder(ArrayDeque(listOf(TransportResponse(201, mapOf("id" to "d1")))))
        assertEquals(
            "d1",
            DeviceLinkClient(DeviceLinkGate(true), ok, signer).register("jwt", "niknolig", "iid", "user", "Phone"),
        )
        assertEquals("jwt", ok.calls[0].second)
        val body = ok.calls[0].third
        val publicKey = java.util.Base64.getUrlDecoder().decode(body.getValue("publicKey"))
        assertArrayEquals(signer.publicKey, publicKey)
        val proof = java.util.Base64.getUrlDecoder().decode(body.getValue("proof"))
        assertEquals(64, proof.size)
        val verifier = Signature.getInstance("Ed25519").apply {
            initVerify(keyPair.public)
            update("niknolig-device-register-v1\nniknolig\niid\nuser".toByteArray(Charsets.UTF_8))
        }
        assertTrue(verifier.verify(proof))
        val bad = Recorder(ArrayDeque(listOf(TransportResponse(401, emptyMap()))))
        try {
            DeviceLinkClient(DeviceLinkGate(true), bad, signer).refresh(DeviceSession("a", "r")); fail()
        } catch (e: DeviceLinkException) {
            assertEquals(401, e.statusCode)
        }
    }

    @Test
    fun malformedSuccessfulResponsesReportProtocolErrorsWithHttpStatus() {
        val missingId = Recorder(ArrayDeque(listOf(TransportResponse(201, emptyMap()))))
        assertProtocolError(201, "id") {
            DeviceLinkClient(DeviceLinkGate(true), missingId, signer)
                .register("jwt", "niknolig", "iid", "user", "Phone")
        }

        val missingNonce = Recorder(ArrayDeque(listOf(TransportResponse(200, emptyMap()))))
        assertProtocolError(200, "nonce") {
            DeviceLinkClient(DeviceLinkGate(true), missingNonce, signer).openSession("dev")
        }

        val missingRefreshToken = Recorder(ArrayDeque(listOf(TransportResponse(200, mapOf("accessToken" to "a")))))
        assertProtocolError(200, "refreshToken") {
            DeviceLinkClient(DeviceLinkGate(true), missingRefreshToken, signer)
                .refresh(DeviceSession("a", "r"))
        }
    }

    private fun assertProtocolError(statusCode: Int, field: String, action: () -> Unit) {
        try {
            action()
            fail("Expected a protocol error for missing $field")
        } catch (error: DeviceLinkProtocolException) {
            assertEquals(statusCode, error.statusCode)
            assertEquals(field, error.field)
            assertTrue(error.message!!.contains(field))
        }
    }

    private fun rawEd25519PublicKey(publicKey: EdECPublicKey): ByteArray {
        val point = publicKey.point
        val encodedY = point.y.toByteArray()
        val unsignedY = if (encodedY.size == 33 && encodedY[0] == 0.toByte()) {
            encodedY.copyOfRange(1, encodedY.size)
        } else {
            encodedY
        }
        require(unsignedY.size <= 32)
        return ByteArray(32).also { raw ->
            unsignedY.reversedArray().copyInto(raw)
            if (point.isXOdd) raw[31] = (raw[31].toInt() or 0x80).toByte()
        }
    }
}

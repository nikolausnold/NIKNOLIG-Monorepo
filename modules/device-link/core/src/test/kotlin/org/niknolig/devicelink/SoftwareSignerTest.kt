package org.niknolig.devicelink

import java.security.KeyFactory
import java.security.Signature
import java.security.spec.X509EncodedKeySpec
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SoftwareSignerTest {
    private val spkiPrefix = byteArrayOf(0x30, 0x2a, 0x30, 0x05, 0x06, 0x03, 0x2b, 0x65, 0x70, 0x03, 0x21, 0x00)

    private fun verify(publicKey: ByteArray, message: ByteArray, signature: ByteArray): Boolean {
        val key = KeyFactory.getInstance("Ed25519").generatePublic(X509EncodedKeySpec(spkiPrefix + publicKey))
        return Signature.getInstance("Ed25519").run {
            initVerify(key); update(message); verify(signature)
        }
    }

    @Test
    fun matchesRfc8032TestVector() {
        val seed = "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60".hexToBytes()
        val expectedPublic = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a".hexToBytes()
        val expectedSignature = ("e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155" +
            "5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b").hexToBytes()
        val signer = SoftwareEd25519Signer(SoftwareEd25519Signer.publicKeyOf(seed)) { seed.copyOf() }
        assertArrayEquals(expectedPublic, signer.publicKey)
        assertArrayEquals(expectedSignature, signer.sign(ByteArray(0)))
    }

    @Test
    fun signaturesVerifyWithTheJdkAndBackendProtocolMessages() {
        val seed = ByteArray(32) { (it * 7 + 1).toByte() }
        val signer = SoftwareEd25519Signer(SoftwareEd25519Signer.publicKeyOf(seed)) { seed.copyOf() }
        val message = DeviceProtocol.sessionMessage("device-1", "nonce-1")
        val signature = signer.sign(message)
        assertEquals(64, signature.size)
        assertTrue(verify(signer.publicKey, message, signature))
        assertFalse(verify(signer.publicKey, message + 1, signature))
    }

    @Test
    fun seedCopyIsWipedAfterSigning() {
        val seed = ByteArray(32) { 5 }
        val handedOut = seed.copyOf()
        SoftwareEd25519Signer(SoftwareEd25519Signer.publicKeyOf(seed)) { handedOut }.sign(byteArrayOf(1))
        assertTrue(handedOut.all { it == 0.toByte() })
    }

    @Test(expected = IllegalArgumentException::class)
    fun rejectsWrongSeedLength() {
        SoftwareEd25519Signer(ByteArray(32)) { ByteArray(16) }.sign(byteArrayOf(1))
    }

    private fun String.hexToBytes() = ByteArray(length / 2) { substring(it * 2, it * 2 + 2).toInt(16).toByte() }
}

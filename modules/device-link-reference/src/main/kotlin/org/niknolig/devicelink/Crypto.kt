package org.niknolig.devicelink

import java.security.KeyFactory
import java.security.KeyPair
import java.security.KeyPairGenerator
import java.security.MessageDigest
import java.security.PublicKey
import java.security.SecureRandom
import java.security.Signature
import java.security.AlgorithmParameters
import java.security.interfaces.ECPublicKey
import java.security.spec.ECGenParameterSpec
import java.security.spec.ECParameterSpec
import java.security.spec.X509EncodedKeySpec
import java.util.Base64

/**
 * Thin wrappers around established JCA primitives (ECDSA P-256, SHA-256,
 * SecureRandom). No cryptographic primitive is implemented here.
 */
object Crypto {
    private const val SIGNATURE_ALGORITHM = "SHA256withECDSA"

    fun sha256(vararg parts: ByteArray): ByteArray {
        val digest = MessageDigest.getInstance("SHA-256")
        parts.forEach { digest.update(it) }
        return digest.digest()
    }

    fun constantTimeEquals(a: ByteArray, b: ByteArray): Boolean = MessageDigest.isEqual(a, b)

    fun verify(publicKeyX509: ByteArray, data: ByteArray, signature: ByteArray): Boolean = runCatching {
        val key = KeyFactory.getInstance("EC").generatePublic(X509EncodedKeySpec(publicKeyX509))
        if (!usesP256(key)) return false
        Signature.getInstance(SIGNATURE_ALGORITHM).run {
            initVerify(key)
            update(data)
            verify(signature)
        }
    }.getOrDefault(false)

    internal fun sign(keyPair: KeyPair, data: ByteArray): ByteArray =
        Signature.getInstance(SIGNATURE_ALGORITHM).run {
            initSign(keyPair.private)
            update(data)
            sign()
        }

    fun isValidPublicKey(publicKeyX509: ByteArray): Boolean = runCatching {
        val key = KeyFactory.getInstance("EC")
            .generatePublic(X509EncodedKeySpec(publicKeyX509))
        usesP256(key)
    }.getOrDefault(false)

    private fun usesP256(publicKey: PublicKey): Boolean {
        val key = publicKey as? ECPublicKey ?: return false
        val expected = AlgorithmParameters.getInstance("EC").apply {
            init(ECGenParameterSpec("secp256r1"))
        }.getParameterSpec(ECParameterSpec::class.java)
        return key.params.curve == expected.curve &&
            key.params.generator == expected.generator &&
            key.params.order == expected.order &&
            key.params.cofactor == expected.cofactor
    }

    fun base64Url(bytes: ByteArray): String = Base64.getUrlEncoder().withoutPadding().encodeToString(bytes)
}

/**
 * Port for the device identity key. The private key never leaves the
 * implementation. On Android the production adapter must generate a
 * non-exportable EC P-256 key in the Android Keystore (see
 * docs/device-link-protocol-and-lifecycle.md); [JcaDeviceKeys] is for tests only.
 */
interface DeviceKeys {
    val publicKey: ByteArray
    fun sign(data: ByteArray): ByteArray
}

class JcaDeviceKeys private constructor(private val pair: KeyPair) : DeviceKeys {
    override val publicKey: ByteArray get() = pair.public.encoded
    override fun sign(data: ByteArray): ByteArray = Crypto.sign(pair, data)

    companion object {
        fun generate(random: SecureRandom = SecureRandom()): JcaDeviceKeys {
            val generator = KeyPairGenerator.getInstance("EC")
            generator.initialize(ECGenParameterSpec("secp256r1"), random)
            return JcaDeviceKeys(generator.generateKeyPair())
        }
    }
}

enum class AppScope { NIKNOLIG, DEFENSE }

/** A device identity is the SHA-256 fingerprint of its public key; a name or UUID is never an identity. */
@JvmInline
value class DeviceId(val value: String) {
    /** Pseudonymous reference that is safe for audit records. */
    fun auditRef(): String = value.take(8)

    companion object {
        fun of(publicKeyX509: ByteArray) = DeviceId(Crypto.base64Url(Crypto.sha256(publicKeyX509)))
    }
}

interface Clock {
    fun monotonicMillis(): Long
    fun wallTimeMillis(): Long
}

object SystemClock : Clock {
    override fun monotonicMillis(): Long = System.nanoTime() / 1_000_000
    override fun wallTimeMillis(): Long = System.currentTimeMillis()
}

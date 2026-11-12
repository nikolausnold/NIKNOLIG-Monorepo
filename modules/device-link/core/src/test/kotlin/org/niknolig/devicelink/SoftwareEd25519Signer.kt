package org.niknolig.devicelink

import org.bouncycastle.crypto.params.Ed25519PrivateKeyParameters
import org.bouncycastle.crypto.signers.Ed25519Signer

/**
 * Test-only Ed25519 signer. Production app keys must remain non-exportable in Android Keystore.
 *
 * The 32-byte seed lives outside this class; [seedSource] must return it from protected storage
 * (the apps keep it AES-GCM encrypted under a non-exportable Keystore key). The seed is wiped
 * from memory after every use.
 */
class SoftwareEd25519Signer(
    override val publicKey: ByteArray,
    private val seedSource: () -> ByteArray,
) : DeviceSigner {
    init {
        require(publicKey.size == SEED_BYTES) { "Ed25519 public key must be 32 bytes" }
    }

    override fun sign(message: ByteArray): ByteArray {
        val seed = seedSource()
        try {
            require(seed.size == SEED_BYTES) { "Ed25519 seed must be 32 bytes" }
            return Ed25519Signer().run {
                init(true, Ed25519PrivateKeyParameters(seed, 0))
                update(message, 0, message.size)
                generateSignature()
            }
        } finally {
            seed.fill(0)
        }
    }

    companion object {
        const val SEED_BYTES = 32

        fun publicKeyOf(seed: ByteArray): ByteArray {
            require(seed.size == SEED_BYTES) { "Ed25519 seed must be 32 bytes" }
            return Ed25519PrivateKeyParameters(seed, 0).generatePublicKey().encoded
        }
    }
}

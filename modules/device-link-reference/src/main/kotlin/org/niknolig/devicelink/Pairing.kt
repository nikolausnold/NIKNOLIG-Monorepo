package org.niknolig.devicelink

import java.io.ByteArrayOutputStream
import java.io.DataOutputStream
import java.security.SecureRandom

const val PROTOCOL_VERSION = 1
private const val NONCE_BYTES = 16
private const val TOKEN_BYTES = 16
private val PAIR_CONTEXT = "NLDL-PAIR-1".toByteArray()

/** Short-lived, single-use pairing token with an attempt limit. Never logged in full. */
class PairingTokenIssuer(
    private val clock: Clock,
    private val random: SecureRandom = SecureRandom(),
    private val ttlMillis: Long = 120_000,
    private val maxAttempts: Int = 3,
) {
    enum class Check { OK, EXPIRED, REUSED, TOO_MANY_ATTEMPTS, NONE }

    private var value: ByteArray? = null
    private var expiresAt = 0L
    private var used = false
    private var failures = 0

    /** Returns the secret to show out-of-band (QR/code). The caller must not log it. */
    fun issue(): ByteArray {
        val token = ByteArray(TOKEN_BYTES).also(random::nextBytes)
        value = token
        expiresAt = clock.nowMillis() + ttlMillis
        used = false
        failures = 0
        return token.copyOf()
    }

    fun hash(): ByteArray? = value?.let { Crypto.sha256(it) }

    fun check(): Check = when {
        value == null -> Check.NONE
        used -> Check.REUSED
        failures >= maxAttempts -> Check.TOO_MANY_ATTEMPTS
        clock.nowMillis() > expiresAt -> Check.EXPIRED
        else -> Check.OK
    }

    fun registerFailure() { failures++ }
    fun markUsed() { used = true }
}

data class Hello(val version: Int, val scope: AppScope, val publicKey: ByteArray, val nonce: ByteArray) {
    fun encode(): ByteArray {
        val out = ByteArrayOutputStream()
        DataOutputStream(out).apply {
            writeInt(version)
            writeByte(scope.ordinal)
            writeInt(publicKey.size); write(publicKey)
            writeInt(nonce.size); write(nonce)
        }
        return out.toByteArray()
    }
}

/** Result of a verified handshake; becomes a trusted peer only after local user confirmation. */
class PendingPairing internal constructor(
    val peerId: DeviceId,
    val peerScope: AppScope,
    internal val peerPublicKey: ByteArray,
    /** Six digits both users compare on screen to detect a man in the middle. */
    val confirmationCode: String,
)

sealed class HandshakeResult {
    data class Verified(val pending: PendingPairing) : HandshakeResult()
    data class Rejected(val reason: AuditResult) : HandshakeResult()
}

/**
 * Mutual authentication: both sides sign a transcript containing both hellos
 * (fresh nonces) and the hash of the shared out-of-band token, so a recorded
 * handshake cannot be replayed and a peer without the token cannot complete it.
 */
class Handshake(
    private val initiator: Boolean,
    private val scope: AppScope,
    private val keys: DeviceKeys,
    private val tokens: PairingTokenIssuer?,
    private val tokenHash: ByteArray,
    private val audit: AuditSink,
    private val replay: ReplayGuard,
    random: SecureRandom = SecureRandom(),
) {
    private val own = Hello(PROTOCOL_VERSION, scope, keys.publicKey, ByteArray(NONCE_BYTES).also(random::nextBytes))
    private var peer: Hello? = null
    private var finished = false

    fun hello(): Hello = own

    fun receiveHello(received: Hello): AuditResult? {
        val reason = when {
            received.version != PROTOCOL_VERSION -> AuditResult.VERSION_UNSUPPORTED
            received.scope == scope -> AuditResult.SCOPE_MISMATCH
            received.nonce.size != NONCE_BYTES || !Crypto.isValidPublicKey(received.publicKey) -> AuditResult.MALFORMED
            Crypto.constantTimeEquals(received.publicKey, own.publicKey) -> AuditResult.SCOPE_MISMATCH
            !replay.acceptNonce(received.nonce) -> AuditResult.REPLAY
            else -> null
        }
        if (reason != null) fail(reason, null) else peer = received
        return reason
    }

    private fun transcript(): ByteArray {
        val p = requireNotNull(peer) { "peer hello missing" }
        val (first, second) = if (initiator) own to p else p to own
        return PAIR_CONTEXT + first.encode() + second.encode() + tokenHash
    }

    private fun roleByte(isInitiator: Boolean): ByteArray = byteArrayOf(if (isInitiator) 1 else 2)

    fun proof(): ByteArray = keys.sign(transcript() + roleByte(initiator))

    fun verifyProof(signature: ByteArray): HandshakeResult {
        val p = peer ?: return reject(AuditResult.MALFORMED, null)
        if (finished) return reject(AuditResult.REPLAY, DeviceId.of(p.publicKey))
        val id = DeviceId.of(p.publicKey)
        tokens?.let {
            val state = it.check()
            if (state != PairingTokenIssuer.Check.OK) {
                return reject(
                    when (state) {
                        PairingTokenIssuer.Check.EXPIRED -> AuditResult.TOKEN_EXPIRED
                        PairingTokenIssuer.Check.REUSED -> AuditResult.TOKEN_REUSED
                        else -> AuditResult.TOKEN_INVALID
                    },
                    id,
                )
            }
        }
        if (!Crypto.verify(p.publicKey, transcript() + roleByte(!initiator), signature)) {
            tokens?.registerFailure()
            return reject(AuditResult.BAD_SIGNATURE, id)
        }
        finished = true
        tokens?.markUsed()
        val digits = Crypto.sha256(transcript()).let {
            ((it[0].toInt() and 0xff shl 16) or (it[1].toInt() and 0xff shl 8) or (it[2].toInt() and 0xff)) % 1_000_000
        }
        return HandshakeResult.Verified(
            PendingPairing(id, p.scope, p.publicKey, "%06d".format(digits)),
        )
    }

    private fun reject(reason: AuditResult, id: DeviceId?): HandshakeResult {
        fail(reason, id)
        return HandshakeResult.Rejected(reason)
    }

    private fun fail(reason: AuditResult, id: DeviceId?) =
        audit.record(AuditType.PAIRING_FAILED, id, reason)
}

/** Rejects reused handshake nonces; bounded so it cannot grow without limit. */
class ReplayGuard(private val capacity: Int = 1000) {
    private val seen = LinkedHashSet<String>()

    fun acceptNonce(nonce: ByteArray): Boolean {
        val key = Crypto.base64Url(nonce)
        if (!seen.add(key)) return false
        if (seen.size > capacity) seen.remove(seen.first())
        return true
    }
}

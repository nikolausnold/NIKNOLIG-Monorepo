package org.niknolig.devicelink

import java.io.ByteArrayOutputStream
import java.io.DataOutputStream
import java.security.SecureRandom
import java.util.Locale

const val PROTOCOL_VERSION = 1
private const val NONCE_BYTES = 16
private const val TOKEN_BYTES = 16
private val PAIR_CONTEXT = "NLDL-PAIR-1".toByteArray()
private val ACCEPT_CONTEXT = "NLDL-PAIR-ACCEPT-1".toByteArray()
private val CONFIRM_CONTEXT = "NLDL-PAIR-CONFIRM-1".toByteArray()

/** Monotonic, process-wide order of handshake starts and revocations (clock independent). */
internal object PairingSequence {
    private val counter = java.util.concurrent.atomic.AtomicLong()
    fun next(): Long = counter.incrementAndGet()
}

/**
 * Short-lived, single-use pairing token with an attempt limit. Never logged in full.
 * Every handshake is bound to the token generation it started with; issuing a new token
 * invalidates all running handshakes. All state changes are atomic, so parallel handshakes
 * cannot exceed the attempt limit or use the token twice.
 */
class PairingTokenIssuer(
    private val clock: Clock,
    private val random: SecureRandom = SecureRandom(),
    private val ttlMillis: Long = 120_000,
    private val maxAttempts: Int = 3,
) {
    enum class Check { OK, EXPIRED, REUSED, TOO_MANY_ATTEMPTS, ROTATED, MISMATCH, NONE }

    private var value: ByteArray? = null
    private var expiresAt = 0L
    private var used = false
    private var attempts = 0
    private var currentGeneration = 0L

    /** Returns the secret to show out-of-band (QR/code). The caller must not log it. */
    @Synchronized
    fun issue(): ByteArray {
        val token = ByteArray(TOKEN_BYTES).also(random::nextBytes)
        value = token
        expiresAt = clock.monotonicMillis() + ttlMillis
        used = false
        attempts = 0
        currentGeneration++
        return token.copyOf()
    }

    @Synchronized
    fun hash(): ByteArray? = value?.let { Crypto.sha256(it) }

    @Synchronized
    fun generation(): Long = currentGeneration

    @Synchronized
    fun check(): Check = when {
        value == null -> Check.NONE
        used -> Check.REUSED
        attempts >= maxAttempts -> Check.TOO_MANY_ATTEMPTS
        clock.monotonicMillis() >= expiresAt -> Check.EXPIRED
        else -> Check.OK
    }

    /**
     * Atomically reserves one verification attempt for a handshake that started with [generation]
     * and [tokenHash]. The attempt is counted before the signature is verified, so failures can
     * never be under-counted by parallel handshakes.
     */
    @Synchronized
    fun beginAttempt(generation: Long, tokenHash: ByteArray): Check {
        val current = value ?: return Check.NONE
        if (generation != currentGeneration) return Check.ROTATED
        val state = check()
        if (state != Check.OK) return state
        attempts++
        return if (Crypto.constantTimeEquals(Crypto.sha256(current), tokenHash)) Check.OK else Check.MISMATCH
    }

    /** Counts a handshake that failed before verification (bad hello, replayed nonce). */
    @Synchronized
    fun registerFailure(generation: Long) {
        if (generation == currentGeneration && value != null && !used && attempts < maxAttempts) attempts++
    }

    /** Atomically consumes the token; only the first successful handshake of a generation wins. */
    @Synchronized
    fun complete(generation: Long): Boolean {
        if (value == null || generation != currentGeneration || used || clock.monotonicMillis() >= expiresAt) return false
        used = true
        return true
    }
}

class Hello(
    val version: Int,
    val scope: AppScope,
    publicKey: ByteArray,
    nonce: ByteArray,
) {
    private val publicKeyBytes = publicKey.copyOf()
    private val nonceBytes = nonce.copyOf()
    val publicKey: ByteArray get() = publicKeyBytes.copyOf()
    val nonce: ByteArray get() = nonceBytes.copyOf()

    fun copy(
        version: Int = this.version,
        scope: AppScope = this.scope,
        publicKey: ByteArray = this.publicKey,
        nonce: ByteArray = this.nonce,
    ) = Hello(version, scope, publicKey, nonce)

    fun encode(): ByteArray {
        val out = ByteArrayOutputStream()
        DataOutputStream(out).apply {
            writeInt(version)
            writeByte(scope.ordinal)
            writeInt(publicKeyBytes.size); write(publicKeyBytes)
            writeInt(nonceBytes.size); write(nonceBytes)
        }
        return out.toByteArray()
    }
}

/** Result of a verified handshake; becomes a trusted peer only after local user confirmation. */
class PendingPairing internal constructor(
    val peerId: DeviceId,
    val peerScope: AppScope,
    internal val peerPublicKey: ByteArray,
    private val localId: DeviceId,
    private val pairingTranscript: ByteArray,
    private val localSigner: (ByteArray) -> ByteArray,
    /** Six digits both users compare on screen to detect a man in the middle. */
    val confirmationCode: String,
    /** Order of the handshake start; a revocation made later invalidates this result. */
    internal val startSequence: Long,
) {
    private var consumed = false
    private var confirmationCreated = false

    @Synchronized
    fun confirmation(userConfirmed: Boolean): PairingConfirmation? {
        if (confirmationCreated) return null
        confirmationCreated = true
        val data = confirmationData(pairingTranscript, localId, peerId, userConfirmed)
        return PairingConfirmation(localId, peerId, userConfirmed, localSigner(data))
    }

    internal fun verifies(confirmation: PairingConfirmation): Boolean =
        confirmation.signerId == peerId &&
            confirmation.recipientId == localId &&
            confirmation.confirmed &&
            Crypto.verify(
                peerPublicKey,
                confirmationData(pairingTranscript, peerId, localId, confirmation.confirmed),
                confirmation.signature,
            )

    /** A pairing result can be used exactly once, whether it is confirmed or declined. */
    @Synchronized
    internal fun consume(): Boolean {
        if (consumed) return false
        consumed = true
        return true
    }
}

class PairingConfirmation internal constructor(
    internal val signerId: DeviceId,
    internal val recipientId: DeviceId,
    internal val confirmed: Boolean,
    internal val signature: ByteArray,
)

private fun confirmationData(
    transcript: ByteArray,
    signer: DeviceId,
    recipient: DeviceId,
    confirmed: Boolean,
) = CONFIRM_CONTEXT + transcript + signer.value.toByteArray() + recipient.value.toByteArray() +
    byteArrayOf(if (confirmed) 1 else 0)

sealed class HandshakeResult {
    data class Verified(val pending: PendingPairing, val issuerAcceptance: ByteArray? = null) : HandshakeResult()
    data object AwaitingIssuerAcceptance : HandshakeResult()
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
    tokenHash: ByteArray,
    private val audit: AuditSink,
    private val replay: ReplayGuard,
    random: SecureRandom = SecureRandom(),
) {
    private val tokenHash = tokenHash.copyOf()
    private val own = Hello(PROTOCOL_VERSION, scope, keys.publicKey, ByteArray(NONCE_BYTES).also(random::nextBytes))
    private val startSequence = PairingSequence.next()
    private val tokenGeneration = tokens?.generation() ?: 0L
    private var peer: Hello? = null
    private var finished = false
    private var awaitingAcceptance = false

    /** Any rejection is final: a handshake never recovers, a retry needs a completely new one. */
    private var dead = false

    fun hello(): Hello = own

    @Synchronized
    fun receiveHello(received: Hello): AuditResult? {
        val reason = when {
            dead || peer != null -> AuditResult.REPLAY
            received.version != PROTOCOL_VERSION -> AuditResult.VERSION_UNSUPPORTED
            received.scope == scope -> AuditResult.SCOPE_MISMATCH
            received.nonce.size != NONCE_BYTES || !Crypto.isValidPublicKey(received.publicKey) -> AuditResult.MALFORMED
            Crypto.constantTimeEquals(received.publicKey, own.publicKey) -> AuditResult.SCOPE_MISMATCH
            Crypto.constantTimeEquals(received.nonce, own.nonce) -> AuditResult.REPLAY
            !replay.acceptNonce(received.nonce) -> if (replay.isFull()) AuditResult.REPLAY_STATE_FULL else AuditResult.REPLAY
            else -> null
        }
        if (reason != null) {
            if (!dead) tokens?.registerFailure(tokenGeneration)
            fail(reason, null)
        } else {
            peer = received
        }
        return reason
    }

    private fun transcript(): ByteArray {
        val p = requireNotNull(peer) { "peer hello missing" }
        val (first, second) = if (initiator) own to p else p to own
        return PAIR_CONTEXT + first.encode() + second.encode() + tokenHash
    }

    private fun roleByte(isInitiator: Boolean): ByteArray = byteArrayOf(if (isInitiator) 1 else 2)

    @Synchronized
    fun proof(): ByteArray {
        check(!dead) { "handshake is no longer valid" }
        return keys.sign(transcript() + roleByte(initiator))
    }

    @Synchronized
    fun verifyProof(signature: ByteArray): HandshakeResult {
        val p = peer
        if (p == null) return reject(AuditResult.MALFORMED, null)
        val id = DeviceId.of(p.publicKey)
        if (dead || finished || awaitingAcceptance) return reject(AuditResult.REPLAY, id)
        if (tokens != null) {
            val state = tokens.beginAttempt(tokenGeneration, tokenHash)
            if (state != PairingTokenIssuer.Check.OK) {
                return reject(
                    when (state) {
                        PairingTokenIssuer.Check.EXPIRED -> AuditResult.TOKEN_EXPIRED
                        PairingTokenIssuer.Check.REUSED -> AuditResult.TOKEN_REUSED
                        PairingTokenIssuer.Check.TOO_MANY_ATTEMPTS -> AuditResult.TOO_MANY_ATTEMPTS
                        else -> AuditResult.TOKEN_INVALID
                    },
                    id,
                )
            }
        }
        if (!Crypto.verify(p.publicKey, transcript() + roleByte(!initiator), signature)) {
            return reject(AuditResult.BAD_SIGNATURE, id)
        }
        if (initiator && tokens != null && !tokens.complete(tokenGeneration)) {
            return reject(AuditResult.TOKEN_REUSED, id)
        }
        if (!initiator) {
            awaitingAcceptance = true
            return HandshakeResult.AwaitingIssuerAcceptance
        }
        finished = true
        val acceptance = keys.sign(acceptanceTranscript())
        return HandshakeResult.Verified(createPending(p), acceptance)
    }

    @Synchronized
    fun verifyIssuerAcceptance(signature: ByteArray): HandshakeResult {
        val p = peer
        if (p == null) return reject(AuditResult.MALFORMED, null)
        val id = DeviceId.of(p.publicKey)
        if (dead || finished || !awaitingAcceptance) return reject(AuditResult.REPLAY, id)
        if (!Crypto.verify(p.publicKey, acceptanceTranscript(), signature)) {
            return reject(AuditResult.BAD_SIGNATURE, id)
        }
        awaitingAcceptance = false
        finished = true
        return HandshakeResult.Verified(createPending(p))
    }

    private fun acceptanceTranscript(): ByteArray =
        ACCEPT_CONTEXT + transcript() + roleByte(isInitiator = true)

    private fun createPending(p: Hello): PendingPairing {
        val digits = Crypto.sha256(transcript()).let {
            ((it[0].toInt() and 0xff shl 16) or (it[1].toInt() and 0xff shl 8) or (it[2].toInt() and 0xff)) % 1_000_000
        }
        return PendingPairing(
            DeviceId.of(p.publicKey),
            p.scope,
            p.publicKey.copyOf(),
            DeviceId.of(keys.publicKey),
            transcript().copyOf(),
            keys::sign,
            String.format(Locale.ROOT, "%06d", digits),
            startSequence,
        )
    }

    private fun reject(reason: AuditResult, id: DeviceId?): HandshakeResult {
        fail(reason, id)
        return HandshakeResult.Rejected(reason)
    }

    private fun fail(reason: AuditResult, id: DeviceId?) {
        dead = true
        audit.record(AuditType.PAIRING_FAILED, id, reason)
    }
}

/**
 * Rejects reused handshake nonces. Entries are never evicted: forgetting an old nonce would make it
 * replayable, so a full guard rejects further hellos (fail closed) until the device is re-initialised.
 */
class ReplayGuard(private val capacity: Int = 1000) {
    private val seen = HashSet<String>()

    @Synchronized
    fun acceptNonce(nonce: ByteArray): Boolean {
        if (seen.size >= capacity) return false
        return seen.add(Crypto.base64Url(nonce))
    }

    @Synchronized
    fun isFull(): Boolean = seen.size >= capacity
}

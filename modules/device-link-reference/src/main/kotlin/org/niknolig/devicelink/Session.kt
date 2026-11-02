package org.niknolig.devicelink

import java.io.ByteArrayOutputStream
import java.io.DataOutputStream
import java.security.SecureRandom

private val AUTH_CONTEXT = "NLDL-AUTH-1".toByteArray()
private val SESSION_AUTH_CONTEXT = "NLDL-SESSION-AUTH-1".toByteArray()
private val SESSION_ACCEPT_CONTEXT = "NLDL-SESSION-ACCEPT-1".toByteArray()
private val REVOCATION_AUTH_CONTEXT = "NLDL-REVOCATION-AUTH-1".toByteArray()

class Challenge internal constructor(
    nonce: ByteArray,
    internal val issuedAt: Long,
    internal val trustGeneration: Long,
    sessionId: ByteArray?,
    internal val revocationOnly: Boolean,
) {
    private val nonceBytes = nonce.copyOf()
    private val sessionIdBytes = sessionId?.copyOf()
    val nonce: ByteArray get() = nonceBytes.copyOf()
    internal val sessionId: ByteArray? get() = sessionIdBytes?.copyOf()
}

class SessionAuthorization internal constructor(
    private val localId: DeviceId,
    private val peerId: DeviceId,
    private val sessionId: ByteArray,
    private val trustGeneration: Long,
) {
    private var consumed = false

    @Synchronized
    internal fun consume(local: DeviceId, peer: DeviceId, id: ByteArray, generation: Long): Boolean {
        if (consumed || local != localId || peer != peerId ||
            !Crypto.constantTimeEquals(id, sessionId) || generation != trustGeneration
        ) return false
        consumed = true
        return true
    }
}

/**
 * Reconnection authentication against pinned keys. Challenges are single-use and short-lived, so a
 * recorded response cannot be replayed. Run it in both directions for mutual authentication.
 */
class PeerAuthenticator(
    private val keys: DeviceKeys,
    private val registry: PeerRegistry,
    private val clock: Clock,
    private val audit: AuditSink,
    private val random: SecureRandom = SecureRandom(),
    private val challengeTtlMillis: Long = 30_000,
) {
    private val ownId = DeviceId.of(keys.publicKey)
    private val outstanding = mutableMapOf<DeviceId, Challenge>()

    @Synchronized
    fun challenge(peer: DeviceId): Challenge? {
        if (registry.state(peer) != PeerState.TRUSTED || registry.trustedKey(peer) == null) {
            audit.record(AuditType.AUTH_FAILED, peer, if (registry.state(peer) == null) AuditResult.UNKNOWN_PEER else AuditResult.PEER_REVOKED)
            return null
        }
        return newChallenge(peer, sessionId = null, revocationOnly = false)
    }

    @Synchronized
    fun sessionChallenge(peer: DeviceId, sessionId: ByteArray): Challenge? {
        if (sessionId.size < SessionIdGuard.MIN_SESSION_ID_BYTES ||
            registry.state(peer) != PeerState.TRUSTED || registry.trustedKey(peer) == null
        ) {
            audit.record(AuditType.AUTH_FAILED, peer, AuditResult.PEER_REVOKED)
            return null
        }
        return newChallenge(peer, sessionId, revocationOnly = false)
    }

    /** Creates a challenge usable only to authenticate delivery of a pending revocation notice. */
    @Synchronized
    fun revocationChallenge(peer: DeviceId): Challenge? {
        if (registry.revocationKey(peer) == null) {
            audit.record(AuditType.AUTH_FAILED, peer, AuditResult.PEER_REVOKED)
            return null
        }
        return newChallenge(peer, sessionId = null, revocationOnly = true)
    }

    /** Answers a challenge issued by [verifier]. */
    fun respond(challenge: Challenge, verifier: DeviceId): ByteArray =
        keys.sign(signedData(challenge, verifier, ownId))

    @Synchronized
    fun verify(peer: DeviceId, response: ByteArray): AuditResult? {
        val challenge = outstanding.remove(peer) // single use, even when verification fails
        val key = registry.trustedKey(peer)
        val failure = when {
            key == null -> if (registry.state(peer) == null) AuditResult.UNKNOWN_PEER else AuditResult.PEER_REVOKED
            challenge == null -> AuditResult.REPLAY
            challenge.sessionId != null || challenge.revocationOnly -> AuditResult.SCOPE_MISMATCH
            !isCurrent(challenge, peer) -> AuditResult.PEER_REVOKED
            clock.monotonicMillis() - challenge.issuedAt >= challengeTtlMillis -> AuditResult.TOKEN_EXPIRED
            !Crypto.verify(key, signedData(challenge, ownId, peer), response) -> AuditResult.BAD_SIGNATURE
            else -> null
        }
        audit.record(
            if (failure == null) AuditType.AUTH_SUCCEEDED else AuditType.AUTH_FAILED,
            peer,
            failure ?: AuditResult.OK,
        )
        return failure
    }

    @Synchronized
    fun sessionAcceptance(
        peer: DeviceId,
        sessionId: ByteArray,
        peerChallenge: Challenge,
        responseToPeerChallenge: ByteArray,
        responseToLocalChallenge: ByteArray,
    ): ByteArray? {
        val localChallenge = outstanding[peer]
        val key = registry.trustedKey(peer)
        if (key == null || localChallenge == null ||
            !isSessionExchangeValid(
                peer,
                sessionId,
                localChallenge,
                peerChallenge,
                responseToPeerChallenge,
                responseToLocalChallenge,
                key,
            )
        ) return null
        return keys.sign(
            sessionAcceptanceData(
                ownId,
                peer,
                sessionId,
                localChallenge,
                peerChallenge,
                responseToPeerChallenge,
                responseToLocalChallenge,
            ),
        )
    }

    @Synchronized
    fun verifySession(
        peer: DeviceId,
        sessionId: ByteArray,
        peerChallenge: Challenge,
        responseToPeerChallenge: ByteArray,
        responseToLocalChallenge: ByteArray,
        peerAcceptance: ByteArray,
    ): SessionAuthorization? {
        val challenge = outstanding.remove(peer)
        val key = registry.trustedKey(peer)
        val failure = when {
            key == null -> AuditResult.PEER_REVOKED
            challenge == null || !isSessionExchangeValid(
                peer,
                sessionId,
                challenge,
                peerChallenge,
                responseToPeerChallenge,
                responseToLocalChallenge,
                key,
            ) -> AuditResult.BAD_SIGNATURE
            !Crypto.verify(
                key,
                sessionAcceptanceData(
                    ownId,
                    peer,
                    sessionId,
                    challenge,
                    peerChallenge,
                    responseToPeerChallenge,
                    responseToLocalChallenge,
                ),
                peerAcceptance,
            ) -> AuditResult.BAD_SIGNATURE
            else -> null
        }
        audit.record(
            if (failure == null) AuditType.AUTH_SUCCEEDED else AuditType.AUTH_FAILED,
            peer,
            failure ?: AuditResult.OK,
        )
        return if (failure == null) {
            SessionAuthorization(ownId, peer, sessionId.copyOf(), challenge!!.trustGeneration)
        } else null
    }

    private fun isSessionExchangeValid(
        peer: DeviceId,
        sessionId: ByteArray,
        localChallenge: Challenge,
        peerChallenge: Challenge,
        responseToPeerChallenge: ByteArray,
        responseToLocalChallenge: ByteArray,
        peerKey: ByteArray,
    ): Boolean =
        localChallenge.sessionId?.let { Crypto.constantTimeEquals(it, sessionId) } == true &&
            peerChallenge.sessionId?.let { Crypto.constantTimeEquals(it, sessionId) } == true &&
            !localChallenge.revocationOnly && !peerChallenge.revocationOnly &&
            !Crypto.constantTimeEquals(localChallenge.nonce, peerChallenge.nonce) &&
            isCurrent(localChallenge, peer) &&
            clock.monotonicMillis() - localChallenge.issuedAt < challengeTtlMillis &&
            Crypto.verify(peerKey, signedData(localChallenge, ownId, peer), responseToLocalChallenge) &&
            Crypto.verify(
                keys.publicKey,
                signedData(peerChallenge, peer, ownId),
                responseToPeerChallenge,
            )

    private fun sessionAcceptanceData(
        local: DeviceId,
        peer: DeviceId,
        sessionId: ByteArray,
        localChallenge: Challenge,
        peerChallenge: Challenge,
        responseToPeerChallenge: ByteArray,
        responseToLocalChallenge: ByteArray,
    ): ByteArray {
        val localIsFirst = local.value < peer.value
        val first = if (localIsFirst) local else peer
        val second = if (localIsFirst) peer else local
        val firstChallenge = if (localIsFirst) localChallenge else peerChallenge
        val secondChallenge = if (localIsFirst) peerChallenge else localChallenge
        val firstResponse = if (localIsFirst) responseToPeerChallenge else responseToLocalChallenge
        val secondResponse = if (localIsFirst) responseToLocalChallenge else responseToPeerChallenge
        val out = ByteArrayOutputStream()
        DataOutputStream(out).apply {
            writeInt(SESSION_ACCEPT_CONTEXT.size); write(SESSION_ACCEPT_CONTEXT)
            writeInt(sessionId.size); write(sessionId)
            listOf(first.value, second.value).forEach {
                val encoded = it.toByteArray()
                writeInt(encoded.size); write(encoded)
            }
            listOf(firstChallenge.nonce, secondChallenge.nonce, firstResponse, secondResponse).forEach {
                writeInt(it.size); write(it)
            }
        }
        return out.toByteArray()
    }

    /** Authenticates a revoked key only for a still-pending revocation notice. */
    @Synchronized
    fun verifyRevocationNotice(peer: DeviceId, response: ByteArray): RevocationDelivery? {
        val challenge = outstanding.remove(peer)
        val key = registry.revocationKey(peer)
        val failure = when {
            key == null -> AuditResult.PEER_REVOKED
            challenge == null || !challenge.revocationOnly -> AuditResult.REPLAY
            !isCurrent(challenge, peer) -> AuditResult.PEER_REVOKED
            clock.monotonicMillis() - challenge.issuedAt >= challengeTtlMillis -> AuditResult.TOKEN_EXPIRED
            !Crypto.verify(key, signedData(challenge, ownId, peer), response) -> AuditResult.BAD_SIGNATURE
            else -> null
        }
        audit.record(
            if (failure == null) AuditType.AUTH_SUCCEEDED else AuditType.AUTH_FAILED,
            peer,
            failure ?: AuditResult.OK,
        )
        return if (failure == null) RevocationDelivery(peer, challenge!!.trustGeneration) else null
    }

    private fun newChallenge(peer: DeviceId, sessionId: ByteArray?, revocationOnly: Boolean) =
        Challenge(
            ByteArray(16).also(random::nextBytes),
            clock.monotonicMillis(),
            registry.trustGeneration(peer),
            sessionId,
            revocationOnly,
        ).also { outstanding[peer] = it }

    private fun isCurrent(challenge: Challenge, peer: DeviceId) =
        challenge.trustGeneration == registry.trustGeneration(peer)

    private fun signedData(challenge: Challenge, verifier: DeviceId, prover: DeviceId): ByteArray {
        val context = when {
            challenge.revocationOnly -> REVOCATION_AUTH_CONTEXT
            challenge.sessionId != null -> SESSION_AUTH_CONTEXT
            else -> AUTH_CONTEXT
        }
        val sessionId = challenge.sessionId ?: ByteArray(0)
        val out = ByteArrayOutputStream()
        DataOutputStream(out).apply {
            writeInt(context.size); write(context)
            writeInt(challenge.nonce.size); write(challenge.nonce)
            writeInt(sessionId.size); write(sessionId)
            writeInt(verifier.value.length); write(verifier.value.toByteArray())
            writeInt(prover.value.length); write(prover.value.toByteArray())
        }
        return out.toByteArray()
    }
}

/**
 * Remembers every session ID this device has used, including closed sessions, so an ID can never be
 * reused and a new session can never reset the counter of an old one. Fail closed when full.
 */
class SessionIdGuard(private val capacity: Int = 1000) {
    private val used = HashSet<String>()

    @Synchronized
    fun register(sessionId: ByteArray): Boolean {
        if (sessionId.size < MIN_SESSION_ID_BYTES || used.size >= capacity) return false
        return used.add(Crypto.base64Url(sessionId))
    }

    companion object {
        const val MIN_SESSION_ID_BYTES = 16
    }
}

class SignedMessage(
    sessionId: ByteArray,
    val counter: Long,
    val scope: DataScope,
    payload: ByteArray,
    signature: ByteArray,
) {
    private val sessionIdBytes = sessionId.copyOf()
    private val payloadBytes = payload.copyOf()
    private val signatureBytes = signature.copyOf()
    val sessionId: ByteArray get() = sessionIdBytes.copyOf()
    val payload: ByteArray get() = payloadBytes.copyOf()
    val signature: ByteArray get() = signatureBytes.copyOf()

    internal fun snapshot() = MessageSnapshot(
        sessionIdBytes.copyOf(),
        counter,
        scope,
        payloadBytes.copyOf(),
        signatureBytes.copyOf(),
    )
}

internal data class MessageSnapshot(
    val sessionId: ByteArray,
    val counter: Long,
    val scope: DataScope,
    val payload: ByteArray,
    val signature: ByteArray,
)

/**
 * Authenticated, replay-protected message layer on top of any transport. It provides integrity and
 * authenticity; confidentiality is the transport's job (see docs/device-link-transport-decision.md).
 * Any failure closes the session; nothing is buffered or retried.
 */
class SecureSession(
    private val keys: DeviceKeys,
    private val peer: DeviceId,
    private val registry: PeerRegistry,
    private val audit: AuditSink,
    sessionId: ByteArray,
    authorization: SessionAuthorization,
    sessionIds: SessionIdGuard,
    private val maxPayloadBytes: Int = 4096,
) {
    private val sessionIdBytes = sessionId.copyOf()
    val sessionId: ByteArray get() = sessionIdBytes.copyOf()

    private var sendCounter = 0L
    private var lastReceived = 0L
    var isOpen = true
        private set

    init {
        val localId = DeviceId.of(keys.publicKey)
        if (!authorization.consume(localId, peer, sessionIdBytes, registry.trustGeneration(peer)) ||
            registry.trustedKey(peer) == null || !sessionIds.register(sessionIdBytes)
        ) fail<Unit>(AuditResult.SESSION_INVALID)
    }

    @Synchronized
    fun close() { isOpen = false }

    private fun data(
        sessionId: ByteArray,
        counter: Long,
        scope: DataScope,
        payload: ByteArray,
        sender: DeviceId,
        recipient: DeviceId,
    ): ByteArray {
        val out = ByteArrayOutputStream()
        DataOutputStream(out).apply {
            write("NLDL-MSG-1".toByteArray())
            writeInt(sessionId.size); write(sessionId)
            writeLong(counter)
            writeInt(scope.ordinal)
            writeInt(sender.value.length); write(sender.value.toByteArray())
            writeInt(recipient.value.length); write(recipient.value.toByteArray())
            writeInt(Direction.SEND.ordinal)
            write(Crypto.sha256(payload))
        }
        return out.toByteArray()
    }

    @Synchronized
    fun seal(scope: DataScope, payload: ByteArray): SignedMessage? {
        if (!isOpen || payload.size > maxPayloadBytes) return fail(AuditResult.MALFORMED)
        if (registry.authorize(peer, scope, Direction.SEND) is Decision.Deny) return fail(null)
        if (sendCounter == Long.MAX_VALUE) return fail(AuditResult.SESSION_INVALID)
        val counter = ++sendCounter
        val payloadSnapshot = payload.copyOf()
        val ownId = DeviceId.of(keys.publicKey)
        return SignedMessage(
            sessionIdBytes.copyOf(),
            counter,
            scope,
            payloadSnapshot,
            keys.sign(data(sessionIdBytes, counter, scope, payloadSnapshot, ownId, peer)),
        )
    }

    /** Returns the payload only if the message is fresh, authentic and currently authorized. */
    @Synchronized
    fun open(message: SignedMessage): ByteArray? {
        if (!isOpen) return fail(AuditResult.SESSION_INVALID)
        val key = registry.trustedKey(peer) ?: return fail(AuditResult.PEER_REVOKED)
        val snapshot = message.snapshot()
        val ownId = DeviceId.of(keys.publicKey)
        return when {
            !Crypto.constantTimeEquals(snapshot.sessionId, sessionIdBytes) -> fail(AuditResult.SESSION_INVALID)
            snapshot.payload.size > maxPayloadBytes -> fail(AuditResult.MALFORMED)
            snapshot.counter <= lastReceived -> fail(AuditResult.REPLAY)
            !Crypto.verify(
                key,
                data(snapshot.sessionId, snapshot.counter, snapshot.scope, snapshot.payload, peer, ownId),
                snapshot.signature,
            ) ->
                fail(AuditResult.BAD_SIGNATURE)
            registry.authorize(peer, snapshot.scope, Direction.RECEIVE) is Decision.Deny -> fail(null)
            else -> { lastReceived = snapshot.counter; snapshot.payload }
        }
    }

    private fun <T> fail(reason: AuditResult?): T? {
        isOpen = false
        if (reason != null) audit.record(AuditType.SESSION_ERROR, peer, reason)
        return null
    }
}

enum class LinkState { IDLE, DISCOVERING, PAIRING, CONNECTED, RECONNECTING, REVOKED, FAILED }

/** Explicit connection states from the design document; any security error ends in FAILED. */
class LinkStateMachine {
    var state = LinkState.IDLE
        private set

    private val allowed = mapOf(
        LinkState.IDLE to setOf(LinkState.DISCOVERING, LinkState.PAIRING),
        LinkState.DISCOVERING to setOf(LinkState.PAIRING, LinkState.IDLE, LinkState.FAILED),
        LinkState.PAIRING to setOf(LinkState.CONNECTED, LinkState.IDLE, LinkState.FAILED),
        LinkState.CONNECTED to setOf(LinkState.RECONNECTING, LinkState.REVOKED, LinkState.FAILED, LinkState.IDLE),
        LinkState.RECONNECTING to setOf(LinkState.CONNECTED, LinkState.REVOKED, LinkState.FAILED, LinkState.IDLE),
        LinkState.REVOKED to setOf(LinkState.IDLE),
        LinkState.FAILED to setOf(LinkState.IDLE),
    )

    fun transition(to: LinkState): Boolean {
        if (to !in allowed.getValue(state)) return false
        state = to
        return true
    }
}

/** Production use stays impossible until every approval in the design document exists in writing. */
object ProductionGate {
    const val ENABLED = false

    fun requireEnabled() {
        check(ENABLED) { "Device link is blocked: SecurityChain-P0 approvals are missing." }
    }
}

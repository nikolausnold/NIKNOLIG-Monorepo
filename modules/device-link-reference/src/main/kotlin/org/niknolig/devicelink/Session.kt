package org.niknolig.devicelink

import java.io.ByteArrayOutputStream
import java.io.DataOutputStream
import java.security.SecureRandom

private val AUTH_CONTEXT = "NLDL-AUTH-1".toByteArray()

class Challenge(val nonce: ByteArray, internal val issuedAt: Long)

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
        if (registry.state(peer) != PeerState.TRUSTED) {
            audit.record(AuditType.AUTH_FAILED, peer, if (registry.state(peer) == null) AuditResult.UNKNOWN_PEER else AuditResult.PEER_REVOKED)
            return null
        }
        return Challenge(ByteArray(16).also(random::nextBytes), clock.nowMillis()).also { outstanding[peer] = it }
    }

    /** Answers a challenge issued by [verifier]. */
    fun respond(challenge: Challenge, verifier: DeviceId): ByteArray = keys.sign(signedData(challenge.nonce, verifier, ownId))

    @Synchronized
    fun verify(peer: DeviceId, response: ByteArray): AuditResult? {
        val challenge = outstanding.remove(peer) // single use, even when verification fails
        val key = registry.trustedKey(peer)
        val failure = when {
            key == null -> if (registry.state(peer) == null) AuditResult.UNKNOWN_PEER else AuditResult.PEER_REVOKED
            challenge == null -> AuditResult.REPLAY
            clock.nowMillis() - challenge.issuedAt > challengeTtlMillis -> AuditResult.TOKEN_EXPIRED
            !Crypto.verify(key, signedData(challenge.nonce, ownId, peer), response) -> AuditResult.BAD_SIGNATURE
            else -> null
        }
        audit.record(
            if (failure == null) AuditType.AUTH_SUCCEEDED else AuditType.AUTH_FAILED,
            peer,
            failure ?: AuditResult.OK,
        )
        return failure
    }

    private fun signedData(nonce: ByteArray, verifier: DeviceId, prover: DeviceId) =
        AUTH_CONTEXT + nonce + verifier.value.toByteArray() + prover.value.toByteArray()
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
        // Too short or already used IDs create a closed session: no message can ever pass.
        if (!sessionIds.register(sessionIdBytes)) fail<Unit>(AuditResult.SESSION_INVALID)
    }

    @Synchronized
    fun close() { isOpen = false }

    private fun data(sessionId: ByteArray, counter: Long, scope: DataScope, payload: ByteArray): ByteArray {
        val out = ByteArrayOutputStream()
        DataOutputStream(out).apply {
            write("NLDL-MSG-1".toByteArray())
            writeInt(sessionId.size); write(sessionId)
            writeLong(counter)
            writeInt(scope.ordinal)
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
        return SignedMessage(
            sessionIdBytes.copyOf(),
            counter,
            scope,
            payload,
            keys.sign(data(sessionIdBytes, counter, scope, payload)),
        )
    }

    /** Returns the payload only if the message is fresh, authentic and currently authorized. */
    @Synchronized
    fun open(message: SignedMessage): ByteArray? {
        if (!isOpen) return fail(AuditResult.SESSION_INVALID)
        val key = registry.trustedKey(peer) ?: return fail(AuditResult.PEER_REVOKED)
        return when {
            !Crypto.constantTimeEquals(message.sessionId, sessionIdBytes) -> fail(AuditResult.SESSION_INVALID)
            message.payload.size > maxPayloadBytes -> fail(AuditResult.MALFORMED)
            message.counter <= lastReceived -> fail(AuditResult.REPLAY)
            !Crypto.verify(key, data(message.sessionId, message.counter, message.scope, message.payload), message.signature) ->
                fail(AuditResult.BAD_SIGNATURE)
            registry.authorize(peer, message.scope, Direction.RECEIVE) is Decision.Deny -> fail(null)
            else -> { lastReceived = message.counter; message.payload }
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

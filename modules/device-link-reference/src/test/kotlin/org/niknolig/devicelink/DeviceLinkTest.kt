package org.niknolig.devicelink

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

class TestClock(var now: Long = 1_000_000L) : Clock {
    override fun nowMillis() = now
}

/** Deterministic in-memory transport used only in tests; it can drop the connection. */
class MockTransport {
    var connected = true
    fun <T> deliver(value: T): T? = if (connected) value else null
}

private val POLICY = RolePolicy(
    setOf(
        Triple(AppScope.NIKNOLIG, DataScope.STATUS_SUMMARY, Direction.SEND),
        Triple(AppScope.DEFENSE, DataScope.STATUS_SUMMARY, Direction.RECEIVE),
        Triple(AppScope.DEFENSE, DataScope.ALERT_NOTIFICATION, Direction.SEND),
        Triple(AppScope.NIKNOLIG, DataScope.ALERT_NOTIFICATION, Direction.RECEIVE),
    ),
)

private class Device(val scope: AppScope, val clock: TestClock, policy: RolePolicy = POLICY) {
    val keys = JcaDeviceKeys.generate()
    val id = DeviceId.of(keys.publicKey)
    val audit = InMemoryAuditLog(clock)
    val registry = PeerRegistry(scope, policy, clock, audit)
    val replay = ReplayGuard()
    val sessionIds = SessionIdGuard()
    val auth = PeerAuthenticator(keys, registry, clock, audit)
}

class DeviceLinkTest {
    private val clock = TestClock()

    private class Pair(val a: Device, val b: Device)

    private fun devices() = Pair(Device(AppScope.NIKNOLIG, clock), Device(AppScope.DEFENSE, clock))

    /** Runs a full handshake; returns both pending pairings or the first rejection. */
    private fun handshake(
        a: Device,
        b: Device,
        issuer: PairingTokenIssuer = PairingTokenIssuer(clock),
        joinerToken: ByteArray? = null,
        tamperProof: Boolean = false,
    ): Triple<HandshakeResult, HandshakeResult, ByteArray> {
        val token = issuer.issue()
        val ha = Handshake(true, a.scope, a.keys, issuer, issuer.hash()!!, a.audit, a.replay)
        val hb = Handshake(false, b.scope, b.keys, null, Crypto.sha256(joinerToken ?: token), b.audit, b.replay)
        ha.receiveHello(hb.hello())
        hb.receiveHello(ha.hello())
        val proofA = ha.proof()
        val proofB = hb.proof().also { if (tamperProof) it[it.size - 1] = (it.last() + 1).toByte() }
        return Triple(ha.verifyProof(proofB), hb.verifyProof(proofA), token)
    }

    private fun paired(): Pair {
        val d = devices()
        val (ra, rb, _) = handshake(d.a, d.b)
        val pa = (ra as HandshakeResult.Verified).pending
        val pb = (rb as HandshakeResult.Verified).pending
        assertEquals(pa.confirmationCode, pb.confirmationCode)
        d.a.registry.completePairing(pa, userConfirmed = true)
        d.b.registry.completePairing(pb, userConfirmed = true)
        return d
    }

    private var idCounter = 0

    private fun freshId(): ByteArray = ByteArray(16) { (idCounter + it).toByte() }.also { idCounter += 17 }

    private fun session(from: Device, to: Device, id: ByteArray = freshId()) =
        SecureSession(from.keys, to.id, from.registry, from.audit, id, from.sessionIds)

    /** Sender on [from] and receiver on [to] sharing one fresh session ID. */
    private fun link(from: Device, to: Device): kotlin.Pair<SecureSession, SecureSession> {
        val id = freshId()
        return session(from, to, id) to session(to, from, id)
    }

    private fun auditTypes(d: Device) = d.audit.snapshot().map { it.type to it.result }

    // ---- pairing ----

    @Test
    fun validPairingRequiresLocalConfirmation() {
        val d = devices()
        val (ra, _, _) = handshake(d.a, d.b)
        val pending = (ra as HandshakeResult.Verified).pending
        assertEquals(d.b.id, pending.peerId)
        assertNull(d.a.registry.completePairing(pending, userConfirmed = false))
        assertNull(d.a.registry.state(d.b.id))
        // A declined result is consumed; the user must run a completely new pairing.
        assertNull(d.a.registry.completePairing(pending, userConfirmed = true))
        assertNull(d.a.registry.state(d.b.id))
        val (again, _, _) = handshake(d.a, d.b)
        assertNotNull(d.a.registry.completePairing((again as HandshakeResult.Verified).pending, userConfirmed = true))
        assertEquals(PeerState.TRUSTED, d.a.registry.state(d.b.id))
    }

    @Test
    fun peerWithoutTheTokenCannotPair() {
        val d = devices()
        val (ra, rb, _) = handshake(d.a, d.b, joinerToken = ByteArray(16) { 7 })
        assertTrue(ra is HandshakeResult.Rejected)
        assertTrue(rb is HandshakeResult.Rejected)
        assertNull(d.a.registry.state(d.b.id))
    }

    @Test
    fun expiredTokenIsRejected() {
        val d = devices()
        val issuer = PairingTokenIssuer(clock, ttlMillis = 1_000)
        val token = issuer.issue()
        val ha = Handshake(true, d.a.scope, d.a.keys, issuer, issuer.hash()!!, d.a.audit, d.a.replay)
        val hb = Handshake(false, d.b.scope, d.b.keys, null, Crypto.sha256(token), d.b.audit, d.b.replay)
        ha.receiveHello(hb.hello()); hb.receiveHello(ha.hello())
        clock.now += 1_001
        assertEquals(HandshakeResult.Rejected(AuditResult.TOKEN_EXPIRED), ha.verifyProof(hb.proof()))
    }

    @Test
    fun tokenIsSingleUse() {
        val d = devices()
        val issuer = PairingTokenIssuer(clock)
        val token = issuer.issue()
        fun attempt(): HandshakeResult {
            val ha = Handshake(true, d.a.scope, d.a.keys, issuer, issuer.hash()!!, d.a.audit, d.a.replay)
            val hb = Handshake(false, d.b.scope, d.b.keys, null, Crypto.sha256(token), d.b.audit, d.b.replay)
            ha.receiveHello(hb.hello()); hb.receiveHello(ha.hello())
            return ha.verifyProof(hb.proof())
        }
        assertTrue(attempt() is HandshakeResult.Verified)
        assertEquals(HandshakeResult.Rejected(AuditResult.TOKEN_REUSED), attempt())
    }

    @Test
    fun recordedHandshakeCannotBeReplayedAgainstFreshNonces() {
        val d = devices()
        val issuer = PairingTokenIssuer(clock)
        val token = issuer.issue()
        val hb = Handshake(false, d.b.scope, d.b.keys, null, Crypto.sha256(token), d.b.audit, d.b.replay)
        val ha1 = Handshake(true, d.a.scope, d.a.keys, issuer, issuer.hash()!!, d.a.audit, d.a.replay)
        ha1.receiveHello(hb.hello()); hb.receiveHello(ha1.hello())
        val recordedProof = hb.proof()
        // Attacker replays B's old hello and proof to a new session of A (fresh nonce, fresh token).
        val issuer2 = PairingTokenIssuer(clock)
        issuer2.issue()
        val ha2 = Handshake(true, d.a.scope, d.a.keys, issuer2, issuer2.hash()!!, d.a.audit, d.a.replay)
        assertEquals(AuditResult.REPLAY, ha2.receiveHello(hb.hello()))
        assertTrue(ha1.verifyProof(recordedProof) is HandshakeResult.Verified)
    }

    @Test
    fun sameScopeMalformedAndUnsupportedHellosAreRejected() {
        val d = devices()
        val other = Device(AppScope.NIKNOLIG, clock)
        fun ha() = Handshake(true, d.a.scope, d.a.keys, null, ByteArray(32), d.a.audit, d.a.replay)
        assertEquals(AuditResult.SCOPE_MISMATCH, ha().receiveHello(Handshake(false, other.scope, other.keys, null, ByteArray(32), other.audit, other.replay).hello()))
        val hello = d.b.let { Handshake(false, it.scope, it.keys, null, ByteArray(32), it.audit, it.replay).hello() }
        assertEquals(AuditResult.VERSION_UNSUPPORTED, ha().receiveHello(hello.copy(version = 99)))
        assertEquals(AuditResult.MALFORMED, ha().receiveHello(hello.copy(nonce = ByteArray(3))))
        assertEquals(AuditResult.MALFORMED, ha().receiveHello(hello.copy(nonce = ByteArray(16) { 9 }, publicKey = byteArrayOf(1, 2))))
    }

    // ---- reconnection / authentication ----

    @Test
    fun mutualReconnectAuthenticationSucceedsAndResponsesAreSingleUse() {
        val d = paired()
        val c = d.a.auth.challenge(d.b.id)!!
        val response = d.b.auth.respond(c, d.a.id)
        assertNull(d.a.auth.verify(d.b.id, response))
        assertEquals(AuditResult.REPLAY, d.a.auth.verify(d.b.id, response))
        val c2 = d.b.auth.challenge(d.a.id)!!
        assertNull(d.b.auth.verify(d.a.id, d.a.auth.respond(c2, d.b.id)))
    }

    @Test
    fun unknownImpostorAndExpiredChallengesAreRejected() {
        val d = paired()
        val impostor = Device(AppScope.DEFENSE, clock)
        assertNull(d.a.auth.challenge(impostor.id))
        assertEquals(AuditResult.UNKNOWN_PEER, d.a.auth.verify(impostor.id, ByteArray(8)))

        // Impostor signs with its own key while claiming B's identity.
        val c = d.a.auth.challenge(d.b.id)!!
        assertEquals(AuditResult.BAD_SIGNATURE, d.a.auth.verify(d.b.id, impostor.auth.respond(c, d.a.id)))

        val c2 = d.a.auth.challenge(d.b.id)!!
        val late = d.b.auth.respond(c2, d.a.id)
        clock.now += 30_001
        assertEquals(AuditResult.TOKEN_EXPIRED, d.a.auth.verify(d.b.id, late))
    }

    @Test
    fun changedPeerKeyIsAnUnknownPeerUntilRepairedWithConsent() {
        val d = paired()
        val rotated = Device(AppScope.DEFENSE, clock)
        assertNull(d.a.registry.state(rotated.id))
        assertEquals(Decision.Deny(AuditResult.UNKNOWN_PEER), d.a.registry.authorize(rotated.id, DataScope.STATUS_SUMMARY, Direction.RECEIVE))
    }

    // ---- consent, roles, revocation ----

    @Test
    fun pairingAloneGrantsNoDataAccess() {
        val d = paired()
        assertEquals(Decision.Deny(AuditResult.NO_CONSENT), d.b.registry.authorize(d.a.id, DataScope.STATUS_SUMMARY, Direction.RECEIVE))
        assertNull(session(d.a, d.b).seal(DataScope.STATUS_SUMMARY, byteArrayOf(1)))
    }

    @Test
    fun scopesAreConsentedSeparatelyAndRolePolicyIsEnforced() {
        val d = paired()
        assertTrue(d.b.registry.grant(d.a.id, DataScope.STATUS_SUMMARY, Direction.RECEIVE, userConfirmed = true))
        assertEquals(Decision.Allow, d.b.registry.authorize(d.a.id, DataScope.STATUS_SUMMARY, Direction.RECEIVE))
        assertEquals(Decision.Deny(AuditResult.WRONG_DIRECTION), d.b.registry.authorize(d.a.id, DataScope.STATUS_SUMMARY, Direction.SEND))
        assertEquals(Decision.Deny(AuditResult.WRONG_DIRECTION), d.b.registry.authorize(d.a.id, DataScope.SENSOR_SUMMARY, Direction.RECEIVE))
        assertFalse(d.b.registry.grant(d.a.id, DataScope.SENSOR_SUMMARY, Direction.RECEIVE, userConfirmed = true))
        assertFalse(d.b.registry.grant(d.a.id, DataScope.ALERT_NOTIFICATION, Direction.SEND, userConfirmed = false))
        assertEquals(Decision.Deny(AuditResult.NO_CONSENT), d.b.registry.authorize(d.a.id, DataScope.ALERT_NOTIFICATION, Direction.SEND))
    }

    @Test
    fun denyAllPolicyAllowsNothingEvenWithConsent() {
        val d = devices()
        val locked = Device(AppScope.DEFENSE, clock, RolePolicy.DENY_ALL)
        val (_, rb, _) = handshake(d.a, locked)
        val pending = (rb as HandshakeResult.Verified).pending
        locked.registry.completePairing(pending, true)
        assertFalse(locked.registry.grant(d.a.id, DataScope.STATUS_SUMMARY, Direction.RECEIVE, true))
    }

    @Test
    fun consentExpires() {
        val d = paired()
        d.b.registry.grant(d.a.id, DataScope.STATUS_SUMMARY, Direction.RECEIVE, true)
        clock.now += 24L * 60 * 60 * 1000 + 1
        assertEquals(Decision.Deny(AuditResult.CONSENT_EXPIRED), d.b.registry.authorize(d.a.id, DataScope.STATUS_SUMMARY, Direction.RECEIVE))
    }

    @Test
    fun revocationBlocksImmediatelyEvenOfflineAndRequiresNewPairing() {
        val d = paired()
        d.b.registry.grant(d.a.id, DataScope.STATUS_SUMMARY, Direction.RECEIVE, true)
        d.a.registry.grant(d.b.id, DataScope.STATUS_SUMMARY, Direction.SEND, true)
        val net = MockTransport()
        net.connected = false // peer unreachable while revoking
        d.b.registry.revokePeer(d.a.id)

        assertEquals(PeerState.REVOKED, d.b.registry.state(d.a.id))
        assertEquals(listOf(d.a.id), d.b.registry.pendingRevocationNotices())
        assertEquals(Decision.Deny(AuditResult.PEER_REVOKED), d.b.registry.authorize(d.a.id, DataScope.STATUS_SUMMARY, Direction.RECEIVE))
        assertNull(d.b.auth.challenge(d.a.id))
        assertFalse(d.b.registry.grant(d.a.id, DataScope.STATUS_SUMMARY, Direction.RECEIVE, true))

        d.b.registry.noticeDelivered(d.a.id)
        assertTrue(d.b.registry.pendingRevocationNotices().isEmpty())

        // New, user-confirmed pairing is the only way back, and consent starts empty.
        val (_, rb, _) = handshake(d.a, d.b)
        d.b.registry.completePairing((rb as HandshakeResult.Verified).pending, true)
        assertEquals(PeerState.TRUSTED, d.b.registry.state(d.a.id))
        assertEquals(Decision.Deny(AuditResult.NO_CONSENT), d.b.registry.authorize(d.a.id, DataScope.STATUS_SUMMARY, Direction.RECEIVE))
    }

    // ---- authorized data access ----

    private fun consented(): Pair {
        val d = paired()
        assertTrue(d.a.registry.grant(d.b.id, DataScope.STATUS_SUMMARY, Direction.SEND, true))
        assertTrue(d.b.registry.grant(d.a.id, DataScope.STATUS_SUMMARY, Direction.RECEIVE, true))
        return d
    }

    @Test
    fun authorizedMessageFlowsAndReplayedOrReorderedMessagesCloseTheSession() {
        val d = consented()
        val net = MockTransport()
        val (sender, receiver) = link(d.a, d.b)
        val m1 = sender.seal(DataScope.STATUS_SUMMARY, "ok".toByteArray())!!
        assertEquals("ok", String(receiver.open(net.deliver(m1)!!)!!))
        assertNull(receiver.open(m1)) // replay
        assertFalse(receiver.isOpen)
        assertNull(receiver.open(sender.seal(DataScope.STATUS_SUMMARY, byteArrayOf(1))!!))
        assertTrue(auditTypes(d.b).contains(AuditType.SESSION_ERROR to AuditResult.REPLAY))
    }

    @Test
    fun tamperedOrForeignSignedMessagesAreRejected() {
        val d = consented()
        val (sender, receiver) = link(d.a, d.b)
        val m = sender.seal(DataScope.STATUS_SUMMARY, "ok".toByteArray())!!
        val tampered = SignedMessage(m.sessionId, m.counter, m.scope, "evil".toByteArray(), m.signature)
        assertNull(receiver.open(tampered))

        val attacker = Device(AppScope.DEFENSE, clock)
        val forged = SecureSession(attacker.keys, d.b.id, attacker.registry, attacker.audit, freshId(), attacker.sessionIds)
        // The attacker is not even allowed to seal; craft a message signed with the wrong key directly.
        val forgedSessionId = freshId()
        val signatureData = java.io.ByteArrayOutputStream().also { bytes ->
            java.io.DataOutputStream(bytes).apply {
                write("NLDL-MSG-1".toByteArray())
                writeInt(forgedSessionId.size)
                write(forgedSessionId)
                writeLong(1)
                writeInt(m.scope.ordinal)
                write(Crypto.sha256(m.payload))
            }
        }.toByteArray()
        val wrongKey = SignedMessage(
            forgedSessionId,
            1,
            m.scope,
            m.payload,
            attacker.keys.sign(signatureData),
        )
        val freshReceiver = session(d.b, d.a, forgedSessionId)
        assertNull(freshReceiver.open(wrongKey))
        assertTrue(auditTypes(d.b).contains(AuditType.SESSION_ERROR to AuditResult.BAD_SIGNATURE))
        assertNull(forged.seal(DataScope.STATUS_SUMMARY, byteArrayOf(1)))
    }

    @Test
    fun unauthorizedScopeAndOversizedPayloadAreRejectedAndAudited() {
        val d = consented()
        val sender = session(d.a, d.b)
        assertNull(sender.seal(DataScope.SENSOR_SUMMARY, byteArrayOf(1)))
        assertFalse(sender.isOpen)
        assertTrue(auditTypes(d.a).contains(AuditType.AUTHORIZATION_DENIED to AuditResult.WRONG_DIRECTION))
        assertNull(session(d.a, d.b).seal(DataScope.STATUS_SUMMARY, ByteArray(5000)))
    }

    @Test
    fun wrongSessionIdIsRejected() {
        val d = consented()
        val m = session(d.a, d.b).seal(DataScope.STATUS_SUMMARY, byteArrayOf(1))!!
        assertNull(session(d.b, d.a).open(m))
    }

    @Test
    fun revocationDuringActiveSessionStopsDelivery() {
        val d = consented()
        val (sender, receiver) = link(d.a, d.b)
        d.b.registry.revokePeer(d.a.id)
        assertNull(receiver.open(sender.seal(DataScope.STATUS_SUMMARY, byteArrayOf(1))!!))
        assertFalse(receiver.isOpen)
    }

    @Test
    fun sessionIdIsDefensivelyCopiedAfterRegistration() {
        val d = consented()
        val suppliedId = freshId()
        val expectedId = suppliedId.copyOf()
        val sender = session(d.a, d.b, suppliedId)
        suppliedId.fill(0)
        val exposedId = sender.sessionId
        exposedId.fill(1)
        assertArrayEquals(expectedId, sender.sessionId)

        val receiver = session(d.b, d.a, expectedId)
        val message = sender.seal(DataScope.STATUS_SUMMARY, byteArrayOf(1))!!
        assertArrayEquals(expectedId, message.sessionId)
        assertNotNull(receiver.open(message))
    }

    @Test
    fun connectionLossEndsInReconnectingWithoutBufferingAndNeedsFreshAuthentication() {
        val d = consented()
        val net = MockTransport()
        val states = LinkStateMachine()
        assertTrue(states.transition(LinkState.PAIRING))
        assertTrue(states.transition(LinkState.CONNECTED))
        net.connected = false
        assertNull(net.deliver(session(d.a, d.b).seal(DataScope.STATUS_SUMMARY, byteArrayOf(1))))
        assertTrue(states.transition(LinkState.RECONNECTING))
        assertFalse(states.transition(LinkState.PAIRING))
        // An old challenge response is useless after reconnecting.
        val c = d.a.auth.challenge(d.b.id)!!
        val old = d.b.auth.respond(c, d.a.id)
        assertNull(d.a.auth.verify(d.b.id, old))
        assertEquals(AuditResult.REPLAY, d.a.auth.verify(d.b.id, old))
        assertTrue(states.transition(LinkState.FAILED))
        assertTrue(states.transition(LinkState.IDLE))
    }

    // ---- P0 security repair regressions ----

    /** Starts a handshake pair against an already issued [token] without issuing a new one. */
    private fun start(d: Pair, issuer: PairingTokenIssuer, token: ByteArray, joinerToken: ByteArray = token): Triple<Handshake, Handshake, Unit> {
        val ha = Handshake(true, d.a.scope, d.a.keys, issuer, issuer.hash()!!, d.a.audit, d.a.replay)
        val hb = Handshake(false, d.b.scope, d.b.keys, null, Crypto.sha256(joinerToken), d.b.audit, d.b.replay)
        ha.receiveHello(hb.hello())
        hb.receiveHello(ha.hello())
        return Triple(ha, hb, Unit)
    }

    private fun finish(h: Triple<Handshake, Handshake, Unit>, tamper: Boolean = false): HandshakeResult {
        val proof = h.second.proof()
        if (tamper) proof[proof.size - 1] = (proof.last() + 1).toByte()
        return h.first.verifyProof(proof)
    }

    // 1. Revocation

    @Test
    fun reusedPairingResultCannotRestoreARevokedPeer() {
        val d = devices()
        val (ra, _, _) = handshake(d.a, d.b)
        val pending = (ra as HandshakeResult.Verified).pending
        assertNotNull(d.a.registry.completePairing(pending, true))
        d.a.registry.revokePeer(d.b.id)
        assertNull(d.a.registry.completePairing(pending, true))
        assertEquals(PeerState.REVOKED, d.a.registry.state(d.b.id))
        assertNull(d.a.auth.challenge(d.b.id))
    }

    @Test
    fun pairingResultFromAHandshakeThatStartedBeforeTheRevocationIsRejected() {
        val d = paired()
        val issuer = PairingTokenIssuer(clock)
        val token = issuer.issue()
        val inFlight = start(d, issuer, token) // parallel handshake already running
        d.a.registry.revokePeer(d.b.id)
        val pending = (finish(inFlight) as HandshakeResult.Verified).pending
        assertNull(d.a.registry.completePairing(pending, true))
        assertEquals(PeerState.REVOKED, d.a.registry.state(d.b.id))

        // Only a completely new handshake, started after the revocation, may restore trust.
        val (fresh, _, _) = handshake(d.a, d.b)
        assertNotNull(d.a.registry.completePairing((fresh as HandshakeResult.Verified).pending, true))
        assertEquals(PeerState.TRUSTED, d.a.registry.state(d.b.id))
    }

    @Test
    fun replayedPairingResultCannotWipeConsentOfATrustedPeer() {
        val d = devices()
        val (ra, _, _) = handshake(d.a, d.b)
        val pending = (ra as HandshakeResult.Verified).pending
        d.a.registry.completePairing(pending, true)
        assertTrue(d.a.registry.grant(d.b.id, DataScope.STATUS_SUMMARY, Direction.SEND, true))
        assertNull(d.a.registry.completePairing(pending, true))
        assertEquals(Decision.Allow, d.a.registry.authorize(d.b.id, DataScope.STATUS_SUMMARY, Direction.SEND))
    }

    // 2. Token rotation

    @Test
    fun tokenRotationRejectsEveryRunningHandshake() {
        val d = devices()
        val issuer = PairingTokenIssuer(clock)
        val token = issuer.issue()
        val running1 = start(d, issuer, token)
        val running2 = start(d, issuer, token)
        issuer.issue() // rotation
        assertEquals(HandshakeResult.Rejected(AuditResult.TOKEN_INVALID), finish(running1))
        assertEquals(HandshakeResult.Rejected(AuditResult.TOKEN_INVALID), finish(running2))
    }

    @Test
    fun oldTokenCannotCompleteAHandshakeAgainstTheRotatedToken() {
        val d = devices()
        val issuer = PairingTokenIssuer(clock)
        val oldToken = issuer.issue()
        issuer.issue()
        assertEquals(HandshakeResult.Rejected(AuditResult.BAD_SIGNATURE), finish(start(d, issuer, oldToken)))
    }

    // 3. Handshake rejection is final

    @Test
    fun rejectedHandshakeStaysInvalidEvenWithAValidProofAfterwards() {
        val d = devices()
        val issuer = PairingTokenIssuer(clock)
        val token = issuer.issue()
        val h = start(d, issuer, token)
        val proof = h.second.proof()
        val bad = proof.copyOf().also { it[it.size - 1] = (it.last() + 1).toByte() }
        assertEquals(HandshakeResult.Rejected(AuditResult.BAD_SIGNATURE), h.first.verifyProof(bad))
        assertEquals(HandshakeResult.Rejected(AuditResult.REPLAY), h.first.verifyProof(proof))
        assertEquals(AuditResult.REPLAY, h.first.receiveHello(h.second.hello()))
        try { h.first.proof(); fail("dead handshake must not sign") } catch (_: IllegalStateException) { }
        assertNull(d.a.registry.state(d.b.id))
        // A new, complete handshake with the still valid token is the only way forward.
        assertTrue(finish(start(d, issuer, token)) is HandshakeResult.Verified)
    }

    @Test
    fun handshakeWithARejectedHelloCannotBeRevived() {
        val d = devices()
        val issuer = PairingTokenIssuer(clock)
        val token = issuer.issue()
        val ha = Handshake(true, d.a.scope, d.a.keys, issuer, issuer.hash()!!, d.a.audit, d.a.replay)
        val hb = Handshake(false, d.b.scope, d.b.keys, null, Crypto.sha256(token), d.b.audit, d.b.replay)
        assertEquals(AuditResult.VERSION_UNSUPPORTED, ha.receiveHello(hb.hello().copy(version = 99)))
        assertEquals(AuditResult.REPLAY, ha.receiveHello(hb.hello()))
        hb.receiveHello(ha.hello())
        assertTrue(ha.verifyProof(hb.proof()) is HandshakeResult.Rejected)
    }

    @Test
    fun secondHelloOnAnEstablishedHandshakeIsRejected() {
        val d = devices()
        val issuer = PairingTokenIssuer(clock)
        val h = start(d, issuer, issuer.issue())
        val other = Device(AppScope.DEFENSE, clock)
        val impostor = Handshake(false, other.scope, other.keys, null, ByteArray(32), other.audit, other.replay)
        assertEquals(AuditResult.REPLAY, h.first.receiveHello(impostor.hello()))
        assertTrue(h.first.verifyProof(h.second.proof()) is HandshakeResult.Rejected)
    }

    // 4. Replay protection

    @Test
    fun replayGuardNeverForgetsANonceAndFailsClosedWhenFull() {
        val guard = ReplayGuard(capacity = 2)
        val n1 = ByteArray(16) { 1 }
        assertTrue(guard.acceptNonce(n1))
        assertTrue(guard.acceptNonce(ByteArray(16) { 2 }))
        assertFalse(guard.acceptNonce(ByteArray(16) { 3 })) // full: no eviction
        assertFalse(guard.acceptNonce(n1)) // the oldest nonce is still remembered
    }

    @Test
    fun helloIsRejectedWhenReplayStateIsFull() {
        val d = devices()
        val full = ReplayGuard(capacity = 0)
        val ha = Handshake(true, d.a.scope, d.a.keys, null, ByteArray(32), d.a.audit, full)
        val hb = Handshake(false, d.b.scope, d.b.keys, null, ByteArray(32), d.b.audit, d.b.replay)
        assertEquals(AuditResult.REPLAY_STATE_FULL, ha.receiveHello(hb.hello()))
    }

    @Test
    fun reflectedOwnNonceIsRejected() {
        val d = devices()
        val ha = Handshake(true, d.a.scope, d.a.keys, null, ByteArray(32), d.a.audit, d.a.replay)
        val hb = Handshake(false, d.b.scope, d.b.keys, null, ByteArray(32), d.b.audit, d.b.replay)
        assertEquals(AuditResult.REPLAY, ha.receiveHello(hb.hello().copy(nonce = ha.hello().nonce)))
    }

    @Test
    fun reusedSessionIdCannotResetReplayProtection() {
        val d = consented()
        val id = freshId()
        val sender = session(d.a, d.b, id)
        val receiver = session(d.b, d.a, id)
        val m1 = sender.seal(DataScope.STATUS_SUMMARY, byteArrayOf(1))!!
        assertNotNull(receiver.open(m1))
        receiver.close()
        // A new session object with the old ID would start at counter 0 and accept m1 again.
        val resurrected = session(d.b, d.a, id)
        assertFalse(resurrected.isOpen)
        assertNull(resurrected.open(m1))
        assertTrue(auditTypes(d.b).contains(AuditType.SESSION_ERROR to AuditResult.SESSION_INVALID))
    }

    @Test
    fun oldSessionMessagesAreRejectedInANewSession() {
        val d = consented()
        val (sender, receiver) = link(d.a, d.b)
        val old = sender.seal(DataScope.STATUS_SUMMARY, byteArrayOf(1))!!
        assertNotNull(receiver.open(old))
        val (_, newReceiver) = link(d.a, d.b)
        assertNull(newReceiver.open(old))
        assertFalse(newReceiver.isOpen)
    }

    @Test
    fun shortSessionIdsAndCounterRollbackAreRejected() {
        val d = consented()
        assertFalse(session(d.a, d.b, byteArrayOf(1, 2, 3)).isOpen)
        val (sender, receiver) = link(d.a, d.b)
        val m1 = sender.seal(DataScope.STATUS_SUMMARY, byteArrayOf(1))!!
        val m2 = sender.seal(DataScope.STATUS_SUMMARY, byteArrayOf(2))!!
        assertNotNull(receiver.open(m2))
        assertNull(receiver.open(m1)) // lower counter after a higher one
        assertFalse(receiver.isOpen)
    }

    @Test
    fun sessionIdGuardFailsClosedWhenFull() {
        val guard = SessionIdGuard(capacity = 1)
        assertTrue(guard.register(ByteArray(16) { 1 }))
        assertFalse(guard.register(ByteArray(16) { 2 }))
        assertFalse(guard.register(ByteArray(16) { 1 }))
    }

    // 5. Attempt limit

    @Test
    fun validProofIsRejectedAfterTheAttemptLimitIsReached() {
        val d = devices()
        val issuer = PairingTokenIssuer(clock, maxAttempts = 2)
        val token = issuer.issue()
        assertEquals(HandshakeResult.Rejected(AuditResult.BAD_SIGNATURE), finish(start(d, issuer, token), tamper = true))
        assertEquals(HandshakeResult.Rejected(AuditResult.BAD_SIGNATURE), finish(start(d, issuer, token), tamper = true))
        // Limit reached: even a completely valid handshake with the correct token is refused now.
        assertEquals(HandshakeResult.Rejected(AuditResult.TOO_MANY_ATTEMPTS), finish(start(d, issuer, token)))
        assertEquals(PairingTokenIssuer.Check.TOO_MANY_ATTEMPTS, issuer.check())
        assertNull(d.a.registry.state(d.b.id))
    }

    @Test
    fun belowTheLimitAValidHandshakeStillSucceeds() {
        val d = devices()
        val issuer = PairingTokenIssuer(clock, maxAttempts = 3)
        val token = issuer.issue()
        finish(start(d, issuer, token), tamper = true)
        finish(start(d, issuer, token), tamper = true)
        assertTrue(finish(start(d, issuer, token)) is HandshakeResult.Verified)
    }

    @Test
    fun wrongTokenAttemptsCountAndExhaustTheLimit() {
        val d = devices()
        val issuer = PairingTokenIssuer(clock, maxAttempts = 2)
        val token = issuer.issue()
        val wrong = ByteArray(16) { 5 }
        assertTrue(finish(start(d, issuer, token, joinerToken = wrong)) is HandshakeResult.Rejected)
        assertTrue(finish(start(d, issuer, token, joinerToken = wrong)) is HandshakeResult.Rejected)
        assertEquals(HandshakeResult.Rejected(AuditResult.TOO_MANY_ATTEMPTS), finish(start(d, issuer, token)))
    }

    @Test
    fun failedHellosCountTowardsTheLimit() {
        val d = devices()
        val issuer = PairingTokenIssuer(clock, maxAttempts = 2)
        val token = issuer.issue()
        repeat(2) {
            val ha = Handshake(true, d.a.scope, d.a.keys, issuer, issuer.hash()!!, d.a.audit, d.a.replay)
            val hb = Handshake(false, d.b.scope, d.b.keys, null, Crypto.sha256(token), d.b.audit, d.b.replay)
            assertEquals(AuditResult.VERSION_UNSUPPORTED, ha.receiveHello(hb.hello().copy(version = 99)))
        }
        assertEquals(HandshakeResult.Rejected(AuditResult.TOO_MANY_ATTEMPTS), finish(start(d, issuer, token)))
    }

    @Test
    fun parallelHandshakesCannotExceedTheAttemptLimit() {
        val d = devices()
        val issuer = PairingTokenIssuer(clock, maxAttempts = 2)
        val token = issuer.issue()
        // Five handshakes all started before any is verified: only two may even be evaluated.
        val running = List(5) { start(d, issuer, token) }
        val results = running.map { finish(it, tamper = true) }
        assertEquals(2, results.count { it == HandshakeResult.Rejected(AuditResult.BAD_SIGNATURE) })
        assertEquals(3, results.count { it == HandshakeResult.Rejected(AuditResult.TOO_MANY_ATTEMPTS) })
    }

    @Test
    fun concurrentValidHandshakesYieldExactlyOneVerifiedResult() {
        val d = devices()
        val issuer = PairingTokenIssuer(clock, maxAttempts = 100)
        val token = issuer.issue()
        val running = List(8) { start(d, issuer, token) }
        val proofs = running.map { it.second.proof() }
        val results = java.util.Collections.synchronizedList(mutableListOf<HandshakeResult>())
        runConcurrently(running.size) { i -> results += running[i].first.verifyProof(proofs[i]) }
        assertEquals(1, results.count { it is HandshakeResult.Verified })
        assertEquals(7, results.count { it == HandshakeResult.Rejected(AuditResult.TOKEN_REUSED) })
    }

    @Test
    fun proofRemainsAvailableAfterSuccessfulVerification() {
        val d = devices()
        val issuer = PairingTokenIssuer(clock)
        val token = issuer.issue()
        val initiator = Handshake(true, d.a.scope, d.a.keys, issuer, issuer.hash()!!, d.a.audit, d.a.replay)
        val responder = Handshake(false, d.b.scope, d.b.keys, null, Crypto.sha256(token), d.b.audit, d.b.replay)
        initiator.receiveHello(responder.hello())
        responder.receiveHello(initiator.hello())

        assertTrue(responder.verifyProof(initiator.proof()) is HandshakeResult.Verified)
        assertTrue(initiator.verifyProof(responder.proof()) is HandshakeResult.Verified)
    }

    @Test
    fun productionGateStaysClosedAfterRepairs() {
        assertFalse(ProductionGate.ENABLED)
    }

    // ---- review follow-up: concurrency, restart, exhausted capacity ----

    private fun runConcurrently(count: Int, block: (Int) -> Unit) {
        val start = java.util.concurrent.CountDownLatch(1)
        val failures = java.util.Collections.synchronizedList(mutableListOf<Throwable>())
        val threads = (0 until count).map { i ->
            Thread {
                try {
                    start.await()
                    block(i)
                } catch (failure: Throwable) {
                    failures += failure
                }
            }
        }
        threads.forEach { it.start() }
        start.countDown()
        threads.forEach { it.join() }
        failures.firstOrNull()?.let { throw AssertionError("Concurrent worker failed", it) }
    }

    @Test
    fun concurrentWorkerFailuresAreRethrownOnTheTestThread() {
        val expected = IllegalStateException("worker failure")
        try {
            runConcurrently(1) { throw expected }
            fail("worker failure was not rethrown")
        } catch (failure: AssertionError) {
            assertSame(expected, failure.cause)
        }
    }

    @Test
    fun registrySerializesRevocationAuthorizationAndConsentChanges() {
        val d = paired()
        runConcurrently(16) {
            when (it % 5) {
                0 -> d.a.registry.revokePeer(d.b.id)
                1 -> d.a.registry.grant(d.b.id, DataScope.STATUS_SUMMARY, Direction.SEND, true)
                2 -> d.a.registry.revokeConsent(d.b.id, DataScope.STATUS_SUMMARY, Direction.SEND)
                3 -> d.a.registry.authorize(d.b.id, DataScope.STATUS_SUMMARY, Direction.SEND)
                else -> {
                    d.a.registry.pendingRevocationNotices()
                    d.a.registry.noticeDelivered(d.b.id)
                }
            }
        }
        assertEquals(PeerState.REVOKED, d.a.registry.state(d.b.id))
        assertNull(d.a.registry.trustedKey(d.b.id))
        assertEquals(
            Decision.Deny(AuditResult.PEER_REVOKED),
            d.a.registry.authorize(d.b.id, DataScope.STATUS_SUMMARY, Direction.SEND),
        )
        assertFalse(d.a.registry.grant(d.b.id, DataScope.STATUS_SUMMARY, Direction.SEND, true))
    }

    @Test
    fun sameMessageDeliveredConcurrentlyIsAcceptedAtMostOnce() {
        val d = consented()
        repeat(20) {
            val (sender, receiver) = link(d.a, d.b)
            val m = sender.seal(DataScope.STATUS_SUMMARY, byteArrayOf(1))!!
            val accepted = java.util.concurrent.atomic.AtomicInteger()
            runConcurrently(8) { if (receiver.open(m) != null) accepted.incrementAndGet() }
            assertEquals(1, accepted.get())
        }
    }

    @Test
    fun reconnectResponseIsAcceptedAtMostOnceEvenConcurrently() {
        val d = paired()
        repeat(20) {
            val c = d.a.auth.challenge(d.b.id)!!
            val response = d.b.auth.respond(c, d.a.id)
            val ok = java.util.concurrent.atomic.AtomicInteger()
            runConcurrently(8) { if (d.a.auth.verify(d.b.id, response) == null) ok.incrementAndGet() }
            assertEquals(1, ok.get())
        }
    }

    @Test
    fun parallelAttemptsNeverExceedTheLimitUnderThreads() {
        val d = devices()
        val issuer = PairingTokenIssuer(clock, maxAttempts = 3)
        val token = issuer.issue()
        val running = List(16) { start(d, issuer, token) }
        val proofs = running.map { it.second.proof().also { p -> p[p.size - 1] = (p.last() + 1).toByte() } }
        val results = java.util.Collections.synchronizedList(mutableListOf<HandshakeResult>())
        runConcurrently(16) { results += running[it].first.verifyProof(proofs[it]) }
        assertEquals(3, results.count { it == HandshakeResult.Rejected(AuditResult.BAD_SIGNATURE) })
        assertEquals(13, results.count { it == HandshakeResult.Rejected(AuditResult.TOO_MANY_ATTEMPTS) })
    }

    @Test
    fun rotationWhileHandshakesAreRunningNeverYieldsAVerifiedResultForTheOldToken() {
        repeat(20) {
            val d = devices()
            val issuer = PairingTokenIssuer(clock, maxAttempts = 100)
            val token = issuer.issue()
            val running = List(6) { start(d, issuer, token) }
            val proofs = running.map { it.second.proof() }
            val results = java.util.Collections.synchronizedList(mutableListOf<HandshakeResult>())
            val rotated = java.util.concurrent.atomic.AtomicBoolean()
            runConcurrently(7) {
                if (it == 6) { issuer.issue(); rotated.set(true) } else results += running[it].first.verifyProof(proofs[it])
            }
            assertTrue(rotated.get())
            // Whatever won the race, the token can have been consumed at most once ...
            assertTrue(results.count { r -> r is HandshakeResult.Verified } <= 1)
            // ... and after the rotation nothing started with the old token verifies.
            assertTrue(finish(start(d, issuer, token)) is HandshakeResult.Rejected)
        }
    }

    @Test
    fun revocationBetweenTwoParallelPairingResultsInvalidatesTheSecond() {
        val d = devices()
        val issuer = PairingTokenIssuer(clock, maxAttempts = 100)
        val token = issuer.issue()
        val h1 = start(d, issuer, token)
        val h2 = start(d, issuer, token)
        val p1 = (finish(h1) as HandshakeResult.Verified).pending
        assertNotNull(d.a.registry.completePairing(p1, true))
        d.a.registry.revokePeer(d.b.id)
        // Token is single use, so h2 cannot even verify now.
        assertEquals(HandshakeResult.Rejected(AuditResult.TOKEN_REUSED), finish(h2))
        assertNull(d.a.registry.completePairing(p1, true))
        assertEquals(PeerState.REVOKED, d.a.registry.state(d.b.id))
    }

    @Test
    fun stalePairingResultCannotReplaceFreshPairingAfterRevocation() {
        val d = paired()
        val staleIssuer = PairingTokenIssuer(clock)
        val staleToken = staleIssuer.issue()
        val stale = (finish(start(d, staleIssuer, staleToken)) as HandshakeResult.Verified).pending
        d.a.registry.revokePeer(d.b.id)

        val (freshResult, _, _) = handshake(d.a, d.b)
        assertNotNull(d.a.registry.completePairing((freshResult as HandshakeResult.Verified).pending, true))
        assertTrue(d.a.registry.grant(d.b.id, DataScope.STATUS_SUMMARY, Direction.SEND, true))
        assertNull(d.a.registry.completePairing(stale, true))
        assertEquals(PeerState.TRUSTED, d.a.registry.state(d.b.id))
        assertEquals(Decision.Allow, d.a.registry.authorize(d.b.id, DataScope.STATUS_SUMMARY, Direction.SEND))
    }

    @Test
    fun exhaustedSessionIdCapacityClosesNewSessionsAndNeverEvicts() {
        val d = consented()
        val tiny = SessionIdGuard(capacity = 2)
        fun make(id: ByteArray) = SecureSession(d.a.keys, d.b.id, d.a.registry, d.a.audit, id, tiny)
        val first = freshId()
        assertTrue(make(first).isOpen)
        assertTrue(make(freshId()).isOpen)
        assertFalse(make(freshId()).isOpen)
        assertFalse(make(first).isOpen)
    }

    @Test
    fun restartLosesAllPendingStateAndOldHandshakesOrTokensAreRejected() {
        val d = devices()
        val issuer = PairingTokenIssuer(clock)
        val token = issuer.issue()
        val running = start(d, issuer, token)
        // "Restart": a fresh issuer without a token, as after process death.
        val restarted = PairingTokenIssuer(clock)
        val ha = Handshake(true, d.a.scope, d.a.keys, restarted, ByteArray(32), d.a.audit, ReplayGuard())
        val hb = Handshake(false, d.b.scope, d.b.keys, null, Crypto.sha256(token), d.b.audit, ReplayGuard())
        ha.receiveHello(hb.hello()); hb.receiveHello(ha.hello())
        assertEquals(HandshakeResult.Rejected(AuditResult.TOKEN_INVALID), ha.verifyProof(hb.proof()))
        assertTrue(finish(running) is HandshakeResult.Verified) // the old object is unaffected, new state is empty
        // A restarted device has no trusted peers: old signed messages are refused.
        val consentedPair = consented()
        val (sender, _) = link(consentedPair.a, consentedPair.b)
        val m = sender.seal(DataScope.STATUS_SUMMARY, byteArrayOf(1))!!
        val rebooted = Device(AppScope.DEFENSE, clock)
        assertNull(SecureSession(rebooted.keys, consentedPair.a.id, rebooted.registry, rebooted.audit, m.sessionId, rebooted.sessionIds).open(m))
    }

    @Test
    fun closedSessionCannotSealOrOpenAnything() {
        val d = consented()
        val (sender, receiver) = link(d.a, d.b)
        val m = sender.seal(DataScope.STATUS_SUMMARY, byteArrayOf(1))!!
        sender.close()
        assertNull(sender.seal(DataScope.STATUS_SUMMARY, byteArrayOf(2)))
        receiver.close()
        assertNull(receiver.open(m))
    }

    // ---- audit policy and production gate ----

    @Test
    fun auditRecordsOnlyTypeTimePseudonymousRefAndResultWithoutSecrets() {
        val d = devices()
        val issuer = PairingTokenIssuer(clock)
        val token = issuer.issue()
        handshake(d.a, d.b, issuer, tamperProof = true)
        val dump = d.a.audit.snapshot().joinToString { it.toString() }
        assertTrue(dump.isNotEmpty())
        assertFalse(dump.contains(Crypto.base64Url(token)))
        assertFalse(dump.contains(d.b.id.value)) // only the 8-character reference
        d.a.audit.snapshot().forEach { assertTrue((it.peerRef ?: "").length <= 8) }
    }

    @Test
    fun auditIsBoundedAndAgeLimited() {
        val log = InMemoryAuditLog(clock, maxEvents = 3, maxAgeMillis = 1_000)
        repeat(5) { log.record(AuditType.AUTH_FAILED, null, AuditResult.BAD_SIGNATURE) }
        assertEquals(3, log.snapshot().size)
        clock.now += 1_001
        assertTrue(log.snapshot().isEmpty())
    }

    @Test
    fun productionStaysBlocked() {
        try {
            ProductionGate.requireEnabled()
            fail("production gate must be closed")
        } catch (_: IllegalStateException) {
        }
        assertFalse(ProductionGate.ENABLED)
    }
}

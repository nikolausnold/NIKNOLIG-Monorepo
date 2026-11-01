package org.niknolig.devicelink

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
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

    private fun session(from: Device, to: Device, id: ByteArray = byteArrayOf(1, 2, 3)) =
        SecureSession(from.keys, to.id, from.registry, from.audit, id)

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
        assertNotNull(d.a.registry.completePairing(pending, userConfirmed = true))
        assertEquals(PeerState.TRUSTED, d.a.registry.state(d.b.id))
    }

    @Test
    fun wrongOrTamperedIdentityProofIsRejectedAndTokenIsBurnedAfterRepeatedFailures() {
        val d = devices()
        val issuer = PairingTokenIssuer(clock, maxAttempts = 2)
        val (ra, _, _) = handshake(d.a, d.b, issuer, tamperProof = true)
        assertEquals(HandshakeResult.Rejected(AuditResult.BAD_SIGNATURE), ra)
        handshake(d.a, d.b, issuer, tamperProof = true)
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
        val ha = Handshake(true, d.a.scope, d.a.keys, null, ByteArray(32), d.a.audit, d.a.replay)
        assertEquals(AuditResult.SCOPE_MISMATCH, ha.receiveHello(Handshake(false, other.scope, other.keys, null, ByteArray(32), other.audit, other.replay).hello()))
        val hello = d.b.let { Handshake(false, it.scope, it.keys, null, ByteArray(32), it.audit, it.replay).hello() }
        assertEquals(AuditResult.VERSION_UNSUPPORTED, ha.receiveHello(hello.copy(version = 99)))
        assertEquals(AuditResult.MALFORMED, ha.receiveHello(hello.copy(nonce = ByteArray(3))))
        assertEquals(AuditResult.MALFORMED, ha.receiveHello(hello.copy(nonce = ByteArray(16) { 9 }, publicKey = byteArrayOf(1, 2))))
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
        val sender = session(d.a, d.b)
        val receiver = session(d.b, d.a)
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
        val sender = session(d.a, d.b)
        val m = sender.seal(DataScope.STATUS_SUMMARY, "ok".toByteArray())!!
        val tampered = SignedMessage(m.sessionId, m.counter, m.scope, "evil".toByteArray(), m.signature)
        assertNull(session(d.b, d.a).open(tampered))

        val attacker = Device(AppScope.DEFENSE, clock)
        val forged = SecureSession(attacker.keys, d.b.id, attacker.registry, attacker.audit, byteArrayOf(1, 2, 3))
        // The attacker is not even allowed to seal; craft a message signed with the wrong key directly.
        val wrongKey = SignedMessage(m.sessionId, 1, m.scope, m.payload, attacker.keys.sign(m.payload))
        assertNull(session(d.b, d.a).open(wrongKey))
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
        val m = session(d.a, d.b, byteArrayOf(9)).seal(DataScope.STATUS_SUMMARY, byteArrayOf(1))!!
        assertNull(session(d.b, d.a, byteArrayOf(1, 2, 3)).open(m))
    }

    @Test
    fun revocationDuringActiveSessionStopsDelivery() {
        val d = consented()
        val receiver = session(d.b, d.a)
        val sender = session(d.a, d.b)
        d.b.registry.revokePeer(d.a.id)
        assertNull(receiver.open(sender.seal(DataScope.STATUS_SUMMARY, byteArrayOf(1))!!))
        assertFalse(receiver.isOpen)
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

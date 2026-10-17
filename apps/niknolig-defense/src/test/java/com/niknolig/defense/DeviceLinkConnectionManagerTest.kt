package com.niknolig.defense

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class DeviceLinkConnectionManagerTest {
    @Test
    fun requiresLocalConsentAndCorrectPeerAppArea() {
        val fixture = Fixture()

        assertFalse(fixture.manager.connect(fixture.peer, localConsentConfirmed = false))
        assertFalse(
            fixture.manager.connect(
                fixture.peer.copy(appArea = APP_DEFENSE),
                localConsentConfirmed = true,
            ),
        )
        assertEquals(0, fixture.ble.connectCalls)
        assertEquals(0, fixture.policy.identityChecks)
    }

    @Test
    fun deniesUntrustedOrUnconsentedPeerBeforeBleConnect() {
        val untrusted = Fixture().apply { policy.identityTrusted = false }
        assertFalse(untrusted.manager.connect(untrusted.peer, localConsentConfirmed = true))
        assertEquals(DeviceLinkState.FAILED, untrusted.manager.state)
        assertEquals(0, untrusted.ble.connectCalls)

        val unconsented = Fixture().apply { policy.peerConsentVerified = false }
        assertFalse(unconsented.manager.connect(unconsented.peer, localConsentConfirmed = true))
        assertEquals(0, unconsented.ble.connectCalls)
    }

    @Test
    fun connectsOnlyAfterTrustAndHandlesTransportFailure() {
        val fixture = Fixture()
        assertTrue(fixture.startConnection())
        assertEquals(DeviceLinkState.CONNECTING, fixture.manager.state)
        fixture.ble.complete(0, true)
        assertEquals(DeviceLinkState.CONNECTED, fixture.manager.state)

        val failed = Fixture()
        assertTrue(failed.manager.connect(failed.peer, localConsentConfirmed = true))
        failed.ble.complete(0, false)
        assertEquals(DeviceLinkState.FAILED, failed.manager.state)
        assertEquals(1, failed.ble.disconnectCalls)
    }

    @Test
    fun rejectsDuplicateSequenceAndDisconnectsSession() {
        val fixture = Fixture()
        fixture.startConnected()

        assertTrue(fixture.manager.receive(fixture.message(sequence = 1)))
        assertFalse(fixture.manager.receive(fixture.message(sequence = 1)))
        assertEquals(DeviceLinkState.FAILED, fixture.manager.state)
        assertEquals(1, fixture.ble.disconnectCalls)
    }

    @Test
    fun rejectsInvalidEnvelopeSignatureAndUnauthorizedEvent() {
        val invalidEnvelope = Fixture().apply { startConnected() }
        assertFalse(
            invalidEnvelope.manager.receive(
                invalidEnvelope.message(sequence = 1).copy(contractVersion = "2.0"),
            ),
        )
        assertEquals(DeviceLinkState.FAILED, invalidEnvelope.manager.state)

        val invalidSignature = Fixture().apply {
            startConnected()
            policy.messageSignatureValid = false
        }
        assertFalse(invalidSignature.manager.receive(invalidSignature.message(sequence = 1)))
        assertEquals(DeviceLinkState.FAILED, invalidSignature.manager.state)

        val unauthorized = Fixture().apply {
            startConnected()
            policy.messageAuthorized = false
        }
        assertFalse(unauthorized.manager.receive(unauthorized.message(sequence = 1)))
        assertEquals(DeviceLinkState.FAILED, unauthorized.manager.state)
    }

    @Test
    fun rejectsExpiredMessagesAndUnknownEvents() {
        val expired = Fixture().apply { startConnected() }
        assertFalse(
            expired.manager.receive(
                expired.message(sequence = 1).copy(expiresAtEpochSeconds = NOW - 1),
            ),
        )
        assertEquals(DeviceLinkState.FAILED, expired.manager.state)

        val unknownEvent = Fixture().apply { startConnected() }
        assertFalse(
            unknownEvent.manager.receive(
                unknownEvent.message(sequence = 1).copy(eventType = "device.unlock"),
            ),
        )
    }

    @Test
    fun revocationDisconnectsAndRejectsReuseOfRevokedSession() {
        val fixture = Fixture()
        fixture.startConnected()
        assertTrue(fixture.manager.receive(fixture.message(sequence = 1, eventType = "session.revoke")))
        assertEquals(DeviceLinkState.REVOKED, fixture.manager.state)
        assertEquals(1, fixture.ble.disconnectCalls)
        assertFalse(fixture.manager.connect(fixture.peer, localConsentConfirmed = true))

        val freshPeer = fixture.peer.copy(sessionId = NEW_SESSION)
        assertTrue(fixture.manager.connect(freshPeer, localConsentConfirmed = true))
    }

    @Test
    fun ignoresLateConnectionCallbackAfterDisconnect() {
        val fixture = Fixture()
        assertTrue(fixture.manager.connect(fixture.peer, localConsentConfirmed = true))
        fixture.manager.disconnect()
        val nextPeer = fixture.peer.copy(sessionId = NEW_SESSION)
        assertTrue(fixture.manager.connect(nextPeer, localConsentConfirmed = true))

        fixture.ble.complete(0, true)
        assertEquals(DeviceLinkState.CONNECTING, fixture.manager.state)
        fixture.ble.complete(1, true)
        assertEquals(DeviceLinkState.CONNECTED, fixture.manager.state)
    }

    private class Fixture {
        val policy = FakePolicy()
        val ble = FakeBle()
        val peer = DeviceLinkPeer(PEER_INSTALLATION, APP_NIKNOLIG, SESSION)
        val manager = DeviceLinkConnectionManager(
            localAppArea = APP_DEFENSE,
            peerAppArea = APP_NIKNOLIG,
            ble = ble,
            securityPolicy = policy,
            nowEpochSeconds = { NOW },
        )

        fun startConnection(): Boolean =
            manager.connect(peer, localConsentConfirmed = true)

        fun startConnected() {
            assertTrue(startConnection())
            ble.complete(0, true)
            assertEquals(DeviceLinkState.CONNECTED, manager.state)
        }

        fun message(
            sequence: Long,
            eventType: String = "session.heartbeat",
        ) = DeviceLinkMessage(
            contractVersion = "1.0",
            messageId = MESSAGE_ID,
            sessionId = peer.sessionId,
            senderInstallationId = peer.installationId,
            senderAppArea = peer.appArea,
            recipientAppArea = APP_DEFENSE,
            sequence = sequence,
            eventType = eventType,
            issuedAtEpochSeconds = NOW,
            expiresAtEpochSeconds = NOW + 60,
            nonce = "A".repeat(22),
            signature = ByteArray(64),
        )
    }

    private class FakeBle : DeviceLinkBleTransport {
        var connectCalls = 0
        var disconnectCalls = 0
        private val callbacks = mutableListOf<(Boolean) -> Unit>()

        override fun connect(peer: DeviceLinkPeer, onResult: (Boolean) -> Unit) {
            connectCalls++
            callbacks += onResult
        }

        override fun disconnect() {
            disconnectCalls++
        }

        fun complete(index: Int, connected: Boolean) {
            callbacks[index](connected)
        }
    }

    private class FakePolicy : DeviceLinkSecurityPolicy {
        var identityTrusted = true
        var peerConsentVerified = true
        var messageSignatureValid = true
        var messageAuthorized = true
        var identityChecks = 0

        override fun verifyPeerIdentity(peer: DeviceLinkPeer, localAppArea: String): Boolean {
            identityChecks++
            return identityTrusted
        }

        override fun verifyPeerConsent(peer: DeviceLinkPeer, localAppArea: String) =
            peerConsentVerified

        override fun verifyMessageSignature(peer: DeviceLinkPeer, message: DeviceLinkMessage) =
            messageSignatureValid

        override fun authorizeMessage(peer: DeviceLinkPeer, message: DeviceLinkMessage) =
            messageAuthorized
    }

    private companion object {
        const val APP_NIKNOLIG = "niknolig"
        const val APP_DEFENSE = "niknolig-defense"
        const val PEER_INSTALLATION = "00000000-0000-4000-8000-000000000031"
        const val SESSION = "00000000-0000-4000-8000-000000000032"
        const val NEW_SESSION = "00000000-0000-4000-8000-000000000033"
        const val MESSAGE_ID = "00000000-0000-4000-8000-000000000034"
        const val NOW = 1_797_000_000L
    }
}

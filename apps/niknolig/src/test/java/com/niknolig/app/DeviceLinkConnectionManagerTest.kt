package com.niknolig.app

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
                fixture.peer.copy(appArea = APP_NIKNOLIG),
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

        val replayedSession = Fixture().apply { policy.sessionReservationAllowed = false }
        assertFalse(replayedSession.manager.connect(replayedSession.peer, localConsentConfirmed = true))
        assertEquals(0, replayedSession.ble.connectCalls)
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
    fun failsClosedWhenConnectedTransportFailsOrSecurityDowngrades() {
        for (failure in listOf("link", "encryption", "mitm", "policy")) {
            val fixture = Fixture().apply { startConnected() }
            val evidence = DeviceLinkTransportEvidence(
                sessionId = fixture.peer.sessionId,
                peerInstallationId = fixture.peer.installationId,
                encrypted = failure != "encryption",
                mitmProtected = failure != "mitm",
            )
            fixture.policy.transportEvidenceVerified = failure != "policy"
            fixture.ble.completeWith(0, if (failure == "link") null else evidence)
            assertEquals(DeviceLinkState.FAILED, fixture.manager.state)
            assertEquals(1, fixture.ble.disconnectCalls)
            assertFalse(fixture.manager.receive(fixture.message(sequence = 1)))
            fixture.ble.complete(0, true)
            assertEquals(DeviceLinkState.FAILED, fixture.manager.state)
        }
    }

    @Test
    fun rechecksIdentityAndConsentWhenConnectionCompletes() {
        for (withdrawIdentity in listOf(false, true)) {
            val fixture = Fixture()
            assertTrue(fixture.startConnection())
            if (withdrawIdentity) {
                fixture.policy.identityTrusted = false
            } else {
                fixture.policy.peerConsentVerified = false
            }
            fixture.ble.complete(0, true)
            assertEquals(DeviceLinkState.FAILED, fixture.manager.state)
            assertEquals(1, fixture.ble.disconnectCalls)
            assertFalse(fixture.manager.receive(fixture.message(sequence = 1)))
        }
    }

    @Test
    fun refusesTransportWithoutVerifiedEncryptionAndMitmProtection() {
        val fixture = Fixture()
        assertTrue(fixture.manager.connect(fixture.peer, localConsentConfirmed = true))
        fixture.ble.completeWith(
            0,
            DeviceLinkTransportEvidence(
                sessionId = fixture.peer.sessionId,
                peerInstallationId = fixture.peer.installationId,
                encrypted = true,
                mitmProtected = false,
            ),
        )
        assertEquals(DeviceLinkState.FAILED, fixture.manager.state)
        assertEquals(1, fixture.ble.disconnectCalls)

        val policyRejectsEvidence = Fixture()
        assertTrue(policyRejectsEvidence.manager.connect(
            policyRejectsEvidence.peer,
            localConsentConfirmed = true,
        ))
        policyRejectsEvidence.policy.transportEvidenceVerified = false
        policyRejectsEvidence.ble.complete(0, true)
        assertEquals(DeviceLinkState.FAILED, policyRejectsEvidence.manager.state)
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
    fun rejectsReusedMessageIdOrNonceEvenWithIncreasingSequence() {
        val reusedId = Fixture()
        reusedId.startConnected()
        assertTrue(reusedId.manager.receive(reusedId.message(sequence = 1)))
        assertFalse(
            reusedId.manager.receive(
                reusedId.message(sequence = 2).copy(nonce = "B".repeat(22)),
            ),
        )
        assertEquals(DeviceLinkState.FAILED, reusedId.manager.state)

        val reusedNonce = Fixture()
        reusedNonce.startConnected()
        assertTrue(reusedNonce.manager.receive(reusedNonce.message(sequence = 1)))
        assertFalse(
            reusedNonce.manager.receive(
                reusedNonce.message(sequence = 2).copy(messageId = NEW_MESSAGE_ID),
            ),
        )
        assertEquals(DeviceLinkState.FAILED, reusedNonce.manager.state)
    }

    @Test
    fun rejectsMixedCaseDuplicateMessageId() {
        for (uppercaseFirst in listOf(false, true)) {
            val fixture = Fixture().apply { startConnected() }
            val lowerId = "abcdef01-2345-4678-9abc-def012345678"
            val upperId = lowerId.uppercase()
            assertTrue(fixture.manager.receive(
                fixture.message(sequence = 1).copy(
                    messageId = if (uppercaseFirst) upperId else lowerId,
                ),
            ))
            assertFalse(fixture.manager.receive(
                fixture.message(sequence = 2).copy(
                    messageId = if (uppercaseFirst) lowerId else upperId,
                    nonce = "B".repeat(22),
                ),
            ))
            assertEquals(DeviceLinkState.FAILED, fixture.manager.state)
            assertEquals(1, fixture.ble.disconnectCalls)
        }
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

        val oversizedSignature = Fixture().apply { startConnected() }
        assertFalse(
            oversizedSignature.manager.receive(
                oversizedSignature.message(sequence = 1).copy(signature = ByteArray(1_000_000)),
            ),
        )
        assertEquals(0, oversizedSignature.policy.messageSignatureChecks)
        assertEquals(DeviceLinkState.FAILED, oversizedSignature.manager.state)
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
    fun revocationInvalidatesTrustAndRequiresRenewedBilateralConsent() {
        for (remote in listOf(false, true)) {
            val fixture = Fixture().apply { startConnected() }
            if (remote) {
                assertTrue(fixture.manager.receive(
                    fixture.message(sequence = 1, eventType = "session.revoke"),
                ))
            } else {
                fixture.manager.revoke()
            }
            assertEquals(DeviceLinkState.REVOKED, fixture.manager.state)
            assertEquals(1, fixture.ble.disconnectCalls)
            assertEquals(listOf(fixture.peer to APP_NIKNOLIG), fixture.policy.revocations)
            assertFalse(fixture.policy.identityTrusted)
            assertFalse(fixture.policy.peerConsentVerified)
            assertFalse(fixture.manager.connect(fixture.peer, localConsentConfirmed = true))

            fixture.manager.disconnect()
            val freshPeer = fixture.peer.copy(sessionId = NEW_SESSION)
            assertFalse(fixture.manager.connect(freshPeer, localConsentConfirmed = true))
            fixture.policy.identityTrusted = true
            assertFalse(fixture.manager.connect(freshPeer, localConsentConfirmed = true))
            fixture.policy.peerConsentVerified = true
            assertFalse(fixture.manager.connect(freshPeer, localConsentConfirmed = false))
            assertFalse(fixture.manager.connect(fixture.peer, localConsentConfirmed = true))
            assertTrue(fixture.manager.connect(freshPeer, localConsentConfirmed = true))
            fixture.ble.complete(0, true)
            assertEquals(DeviceLinkState.CONNECTING, fixture.manager.state)
            fixture.ble.complete(1, true)
            assertEquals(DeviceLinkState.CONNECTED, fixture.manager.state)
        }
    }

    @Test
    fun revocationFailureBlocksReconnectUntilPolicyInvalidationSucceeds() {
        for (remote in listOf(false, true)) {
            for (throws in listOf(false, true)) {
                val fixture = Fixture().apply { startConnected() }
                fixture.policy.revocationAllowed = false
                fixture.policy.revocationThrows = throws
                if (remote) {
                    assertFalse(fixture.manager.receive(
                        fixture.message(sequence = 1, eventType = "session.revoke"),
                    ))
                } else {
                    fixture.manager.revoke()
                }
                assertEquals(DeviceLinkState.FAILED, fixture.manager.state)
                assertEquals(1, fixture.ble.disconnectCalls)
                assertFalse(fixture.manager.receive(fixture.message(sequence = 2)))
                fixture.manager.disconnect()
                val freshPeer = fixture.peer.copy(sessionId = NEW_SESSION)
                assertFalse(fixture.manager.connect(freshPeer, localConsentConfirmed = true))
                assertEquals(1, fixture.ble.connectCalls)
                assertTrue(fixture.policy.identityTrusted)
                assertTrue(fixture.policy.peerConsentVerified)

                fixture.policy.revocationThrows = false
                fixture.policy.revocationAllowed = true
                assertFalse(fixture.manager.connect(freshPeer, localConsentConfirmed = true))
                assertFalse(fixture.policy.identityTrusted)
                assertFalse(fixture.policy.peerConsentVerified)
                fixture.policy.identityTrusted = true
                fixture.policy.peerConsentVerified = true
                assertTrue(fixture.manager.connect(freshPeer, localConsentConfirmed = true))
            }
        }
    }

    @Test
    fun sessionReservationAllowsMoreThanFormerLimitAndRejectsReuse() {
        val fixture = Fixture()
        repeat(130) { index ->
            val peer = fixture.peer.copy(sessionId = sessionId(index))
            assertTrue(fixture.manager.connect(peer, localConsentConfirmed = true))
            fixture.ble.complete(index, true)
            assertEquals(DeviceLinkState.CONNECTED, fixture.manager.state)
            fixture.manager.disconnect()
        }

        assertFalse(fixture.manager.connect(fixture.peer, localConsentConfirmed = true))
        assertEquals(130, fixture.ble.connectCalls)
    }

    @Test
    fun ignoresLateConnectionCallbackAfterDisconnect() {
        for (reuseSession in listOf(false, true)) {
            val fixture = Fixture()
            assertTrue(fixture.startConnection())
            fixture.manager.disconnect()
            fixture.policy.reservedSessions.clear()
            val nextPeer = if (reuseSession) fixture.peer else fixture.peer.copy(sessionId = NEW_SESSION)
            assertTrue(fixture.manager.connect(nextPeer, localConsentConfirmed = true))

            fixture.ble.complete(0, true)
            fixture.ble.complete(0, false)
            assertEquals(DeviceLinkState.CONNECTING, fixture.manager.state)
            assertEquals(1, fixture.ble.disconnectCalls)
            fixture.ble.complete(1, true)
            assertEquals(DeviceLinkState.CONNECTED, fixture.manager.state)
            fixture.ble.complete(0, false)
            assertEquals(DeviceLinkState.CONNECTED, fixture.manager.state)
            assertEquals(1, fixture.ble.disconnectCalls)
        }
    }

    private class Fixture {
        val policy = FakePolicy()
        val ble = FakeBle()
        val peer = DeviceLinkPeer(PEER_INSTALLATION, APP_DEFENSE, SESSION)
        val manager = DeviceLinkConnectionManager(
            localAppArea = APP_NIKNOLIG,
            peerAppArea = APP_DEFENSE,
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
            recipientAppArea = APP_NIKNOLIG,
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
        private val callbacks = mutableListOf<(DeviceLinkTransportEvidence?) -> Unit>()
        private val peers = mutableListOf<DeviceLinkPeer>()

        override fun connect(
            peer: DeviceLinkPeer,
            onResult: (DeviceLinkTransportEvidence?) -> Unit,
        ) {
            connectCalls++
            peers += peer
            callbacks += onResult
        }

        override fun disconnect() {
            disconnectCalls++
        }

        fun complete(index: Int, connected: Boolean) {
            val peer = peers[index]
            callbacks[index](
                if (connected) {
                    DeviceLinkTransportEvidence(
                        sessionId = peer.sessionId,
                        peerInstallationId = peer.installationId,
                        encrypted = true,
                        mitmProtected = true,
                    )
                } else {
                    null
                },
            )
        }

        fun completeWith(index: Int, evidence: DeviceLinkTransportEvidence?) {
            callbacks[index](evidence)
        }
    }

    private class FakePolicy : DeviceLinkSecurityPolicy {
        var identityTrusted = true
        var peerConsentVerified = true
        var sessionReservationAllowed = true
        var transportEvidenceVerified = true
        var messageSignatureValid = true
        var messageAuthorized = true
        var identityChecks = 0
        var messageSignatureChecks = 0
        var revocationAllowed = true
        var revocationThrows = false
        val revocations = mutableListOf<Pair<DeviceLinkPeer, String>>()
        val reservedSessions = mutableSetOf<String>()

        override fun verifyPeerIdentity(peer: DeviceLinkPeer, localAppArea: String): Boolean {
            identityChecks++
            return identityTrusted
        }

        override fun verifyPeerConsent(peer: DeviceLinkPeer, localAppArea: String) =
            peerConsentVerified

        override fun revokePeerTrustAndConsent(peer: DeviceLinkPeer, localAppArea: String): Boolean {
            revocations += peer to localAppArea
            if (revocationThrows) throw IllegalStateException("Revocation unavailable")
            if (!revocationAllowed) return false
            identityTrusted = false
            peerConsentVerified = false
            return true
        }

        override fun reserveFreshSession(peer: DeviceLinkPeer): Boolean =
            sessionReservationAllowed && reservedSessions.add(peer.sessionId)

        override fun verifyTransportEvidence(
            peer: DeviceLinkPeer,
            evidence: DeviceLinkTransportEvidence,
        ) = transportEvidenceVerified

        override fun verifyMessageSignature(peer: DeviceLinkPeer, message: DeviceLinkMessage): Boolean {
            messageSignatureChecks++
            return messageSignatureValid
        }

        override fun authorizeMessage(peer: DeviceLinkPeer, message: DeviceLinkMessage) =
            messageAuthorized
    }

    private companion object {
        fun sessionId(index: Int) =
            "00000000-0000-4000-8000-${index.toString().padStart(12, '0')}"

        const val APP_NIKNOLIG = "niknolig"
        const val APP_DEFENSE = "niknolig-defense"
        const val PEER_INSTALLATION = "00000000-0000-4000-8000-000000000021"
        const val SESSION = "00000000-0000-4000-8000-000000000022"
        const val NEW_SESSION = "00000000-0000-4000-8000-000000000023"
        const val MESSAGE_ID = "00000000-0000-4000-8000-000000000024"
        const val NEW_MESSAGE_ID = "00000000-0000-4000-8000-000000000025"
        const val NOW = 1_797_000_000L
    }
}

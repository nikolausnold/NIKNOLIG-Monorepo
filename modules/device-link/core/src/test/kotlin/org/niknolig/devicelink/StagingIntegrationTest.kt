package org.niknolig.devicelink

import java.security.SecureRandom
import java.util.UUID
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Assume.assumeTrue
import org.junit.Test

/**
 * End-to-end test of the real client code (HTTPS transport, Ed25519 proofs, sessions) against a deployed
 * backend. It only runs when the staging environment is configured and is skipped otherwise; a skip is
 * not a pass. Required: NIKNOLIG_STAGING_URL, NIKNOLIG_STAGING_TOKEN_APP, NIKNOLIG_STAGING_TOKEN_DEFENSE
 * (account JWTs with app_metadata.app_area set to the respective app).
 */
class StagingIntegrationTest {
    private class MemoryStore : LinkStateStore {
        private var id: String? = null
        private var session: DeviceSession? = null
        override fun deviceId() = id
        override fun saveDeviceId(id: String) { this.id = id }
        override fun session() = session
        override fun saveSession(session: DeviceSession) { this.session = session }
        override fun clearSession() { session = null }
        override fun clear() { id = null; session = null }
    }

    private class Device(url: String, val area: String) {
        val seed = ByteArray(32).also { SecureRandom().nextBytes(it) }
        val signer = SoftwareEd25519Signer(SoftwareEd25519Signer.publicKeyOf(seed)) { seed.copyOf() }
        val service = DeviceLinkService(DeviceLinkGate(true), HttpsTransport(url, 15_000), signer, MemoryStore())
    }

    @Test
    fun pairShareReadRevokeAgainstStaging() {
        val url = System.getenv("NIKNOLIG_STAGING_URL")
        val appToken = System.getenv("NIKNOLIG_STAGING_TOKEN_APP")
        val defenseToken = System.getenv("NIKNOLIG_STAGING_TOKEN_DEFENSE")
        assumeTrue("staging environment not configured", !url.isNullOrBlank() && !appToken.isNullOrBlank() && !defenseToken.isNullOrBlank())

        val app = Device(url!!, "niknolig")
        val defense = Device(url, "niknolig-defense")
        try {
            app.service.register(appToken!!, app.area, UUID.randomUUID().toString(), "staging-test-app")
            defense.service.register(defenseToken!!, defense.area, UUID.randomUUID().toString(), "staging-test-defense")

            val offer = app.service.createPairing()
            assertTrue(PairingQr.normalizeCode(offer.code) != null)
            val claimed = defense.service.claimPairing(PairingQr.parse(PairingQr(offer.code, app.area).encode(), defense.area)!!.code)
            assertEquals("claimed", claimed.state)
            val sasApp = app.service.pairing(offer.pairingId).shortAuthString
            val sasDefense = claimed.shortAuthString
            assertNotNull(sasApp)
            assertTrue(sasApp!!.matches(Regex("\\d{6}")))
            assertNotNull(sasDefense)
            assertTrue(sasDefense!!.matches(Regex("\\d{6}")))
            assertEquals(sasApp, sasDefense)

            app.service.confirmPairing(offer.pairingId)
            val done = defense.service.confirmPairing(claimed.pairingId)
            assertEquals("confirmed", done.state)

            val link = defense.service.links().single { it.peer.appArea == app.area }
            val grant = defense.service.createGrant(link.linkId, DeviceLinkScopes.STATUS_READ, 300)
            defense.service.reportStatus("ok", "staging test")
            val appLink = app.service.links().single { it.peer.appArea == defense.area }
            assertEquals("ok", app.service.peerStatus(appLink.linkId).state)

            defense.service.revokeGrant(grant.grantId)
            try {
                app.service.peerStatus(appLink.linkId)
                fail("status must be refused after the grant is revoked")
            } catch (error: DeviceLinkException) {
                assertEquals(403, error.statusCode)
            }
            defense.service.revokeLink(link.linkId)
            assertTrue(app.service.links().none { it.linkId == appLink.linkId && it.state == "active" })
        } finally {
            runCatching { app.service.revokeThisDevice() }
            runCatching { defense.service.revokeThisDevice() }
        }
    }
}

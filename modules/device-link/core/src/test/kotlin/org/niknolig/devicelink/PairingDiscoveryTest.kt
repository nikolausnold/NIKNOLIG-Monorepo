package org.niknolig.devicelink

import java.util.Base64
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.fail
import org.junit.Test

class PairingDiscoveryTest {
    @Test
    fun qrRoundTripAndNormalisation() {
        val qr = PairingQr("ABCD2345", "niknolig-defense")
        assertEquals(qr, PairingQr.parse(qr.encode(), "niknolig"))
        assertEquals("ABCD2345", PairingQr.normalizeCode("abcd-2345"))
        assertNull(PairingQr.normalizeCode("ABCD234"))
        assertNull(PairingQr.normalizeCode("ABCD234O"))
        assertNull(PairingQr.normalizeCode("ABCD234I"))
    }

    @Test
    fun qrRejectsMalformedForeignAndSameAreaPayloads() {
        val good = "niknolig-pair://pair?v=1&area=niknolig-defense&code=ABCD2345"
        assertEquals("ABCD2345", PairingQr.parse(good, "niknolig")!!.code)
        listOf(
            good.replace("niknolig-pair", "https"),
            good.replace("//pair", "//other"),
            good.replace("v=1", "v=2"),
            good.replace("area=niknolig-defense", "area=niknolig"),
            good.replace("area=niknolig-defense", "area=evil"),
            good.replace("ABCD2345", "ABCD23"),
            "$good&extra=1",
            "$good#frag",
            good.replace("&code=ABCD2345", ""),
            "niknolig-pair://user@pair?v=1&area=niknolig-defense&code=ABCD2345",
            "not a uri",
            good + "A".repeat(300),
        ).forEach { assertNull(it, PairingQr.parse(it, "niknolig")) }
        assertNull(PairingQr.parse(good, "niknolig-defense"))
    }

    @Test
    fun discoveryAcceptsOnlyTheOtherAppAndSanitisesNames() {
        fun txt(vararg pairs: Pair<String, String>) = pairs.associate { it.first to it.second.toByteArray() }
        val ok = DiscoveryAnnouncement.parse(txt("v" to "1", "area" to "niknolig-defense", "name" to "Pixel\u202E 7\n"), "niknolig")!!
        assertEquals("niknolig-defense", ok.area)
        assertEquals("Pixel 7", ok.displayName)
        assertNull(DiscoveryAnnouncement.parse(txt("v" to "1", "area" to "niknolig", "name" to "x"), "niknolig"))
        assertNull(DiscoveryAnnouncement.parse(txt("v" to "2", "area" to "niknolig-defense", "name" to "x"), "niknolig"))
        assertNull(DiscoveryAnnouncement.parse(txt("area" to "niknolig-defense", "name" to "x"), "niknolig"))
        assertNull(DiscoveryAnnouncement.parse(txt("v" to "1", "area" to "niknolig-defense", "name" to "x".repeat(100)), "niknolig"))
        assertEquals("niknolig-defense", DiscoveryAnnouncement.parse(txt("v" to "1", "area" to "niknolig-defense", "name" to "\n"), "niknolig")!!.displayName)
    }

    @Test
    fun announcementNeverCarriesSecrets() {
        val txt = DiscoveryAnnouncement("niknolig", "Phone").txt()
        assertEquals(setOf("v", "area", "name"), txt.keys)
    }

    private fun token(payload: String) =
        "h." + Base64.getUrlEncoder().withoutPadding().encodeToString(payload.toByteArray()) + ".s"

    @Test
    fun appAreaClaimIsCheckedBeforeRegistration() {
        val ok = token("""{"sub":"u","exp":2000,"app_metadata":{"app_area":"niknolig"}}""")
        AppAreaClaim.require(ok, "niknolig", 1000)
        fun reason(token: String, area: String = "niknolig"): AppAreaClaimException.Reason {
            try {
                AppAreaClaim.require(token, area, 1000)
            } catch (e: AppAreaClaimException) {
                return e.reason
            }
            fail("expected rejection"); throw AssertionError()
        }
        assertEquals(AppAreaClaimException.Reason.MISMATCH, reason(ok, "niknolig-defense"))
        assertEquals(AppAreaClaimException.Reason.MISSING, reason(token("""{"sub":"u","app_metadata":{}}""")))
        assertEquals(AppAreaClaimException.Reason.MISSING, reason(token("""{"sub":"u"}""")))
        assertEquals(AppAreaClaimException.Reason.EXPIRED, reason(token("""{"exp":999,"app_metadata":{"app_area":"niknolig"}}""")))
    }
}

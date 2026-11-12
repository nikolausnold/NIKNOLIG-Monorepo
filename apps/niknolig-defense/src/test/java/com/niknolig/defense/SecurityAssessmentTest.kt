package com.niknolig.defense

import org.junit.Assert.assertEquals
import org.junit.Test

class SecurityAssessmentTest {
    @Test
    fun reportsOnlyFindingsSupportedByDeviceFacts() {
        val facts = SecurityFacts(
            androidRelease = "15",
            sdkLevel = 35,
            securityPatch = "2026-10-05",
            secureScreenLock = false,
            debuggableBuild = true,
        )

        assertEquals(
            listOf(
                SecurityFinding.NO_SECURE_SCREEN_LOCK,
                SecurityFinding.DEBUGGABLE_BUILD,
            ),
            SecurityAssessment.findings(facts),
        )
    }

    @Test
    fun representsMissingInformationAsUnknownRatherThanSafe() {
        val facts = SecurityFacts(
            androidRelease = null,
            sdkLevel = null,
            securityPatch = null,
            secureScreenLock = null,
            debuggableBuild = null,
        )

        assertEquals(
            listOf(
                SecurityFinding.SCREEN_LOCK_STATE_UNKNOWN,
                SecurityFinding.BUILD_STATE_UNKNOWN,
                SecurityFinding.SECURITY_PATCH_UNKNOWN,
            ),
            SecurityAssessment.findings(facts),
        )
    }

    @Test
    fun reportsNoFindingsOnlyWhenEachAvailableSignalHasNoFinding() {
        val facts = SecurityFacts(
            androidRelease = "15",
            sdkLevel = 35,
            securityPatch = "2026-10-05",
            secureScreenLock = true,
            debuggableBuild = false,
        )

        assertEquals(emptyList<SecurityFinding>(), SecurityAssessment.findings(facts))
    }
}

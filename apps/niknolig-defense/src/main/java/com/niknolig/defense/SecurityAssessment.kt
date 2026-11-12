package com.niknolig.defense

internal data class SecurityFacts(
    val androidRelease: String?,
    val sdkLevel: Int?,
    val securityPatch: String?,
    val secureScreenLock: Boolean?,
    val debuggableBuild: Boolean?,
)

internal enum class SecurityFinding {
    NO_SECURE_SCREEN_LOCK,
    SCREEN_LOCK_STATE_UNKNOWN,
    DEBUGGABLE_BUILD,
    BUILD_STATE_UNKNOWN,
    SECURITY_PATCH_UNKNOWN,
}

internal object SecurityAssessment {
    fun findings(facts: SecurityFacts): List<SecurityFinding> = buildList {
        when (facts.secureScreenLock) {
            false -> add(SecurityFinding.NO_SECURE_SCREEN_LOCK)
            null -> add(SecurityFinding.SCREEN_LOCK_STATE_UNKNOWN)
            true -> Unit
        }
        when (facts.debuggableBuild) {
            true -> add(SecurityFinding.DEBUGGABLE_BUILD)
            null -> add(SecurityFinding.BUILD_STATE_UNKNOWN)
            false -> Unit
        }
        if (facts.securityPatch.isNullOrBlank()) {
            add(SecurityFinding.SECURITY_PATCH_UNKNOWN)
        }
    }
}

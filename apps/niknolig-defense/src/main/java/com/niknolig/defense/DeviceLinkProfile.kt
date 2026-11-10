package com.niknolig.defense

import android.content.Context

internal object DeviceLinkProfile {
    const val APP_AREA = "niknolig-defense"
    const val DEVICE_KEY_ALIAS = "niknolig_defense_device_key_v1"
    const val STATE_KEY_ALIAS = "niknolig_defense_link_state_v1"
    const val SEED_KEY_ALIAS = "niknolig_defense_device_seed_v1"

    /** Local diagnosis only: three device checks, not a claim of complete protection. */
    fun statusReport(context: Context): Pair<String, String?>? {
        val findings = SecurityAssessment.findings(AndroidSecurityDiagnostics.capture(context))
        val concrete = findings.filter {
            it == SecurityFinding.NO_SECURE_SCREEN_LOCK || it == SecurityFinding.DEBUGGABLE_BUILD
        }
        return when {
            concrete.isNotEmpty() -> "warning" to "Lokale Diagnose: ${concrete.size} Sicherheitshinweis(e)"
            findings.isNotEmpty() -> "unknown" to "Lokale Diagnose unvollständig"
            else -> "ok" to "Lokale Diagnose ohne Auffälligkeiten (3 Prüfungen)"
        }
    }
}

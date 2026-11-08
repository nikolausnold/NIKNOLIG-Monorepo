package com.niknolig.defense

import android.app.KeyguardManager
import android.content.Context
import android.content.pm.ApplicationInfo
import android.os.Build
import org.json.JSONArray
import org.json.JSONObject

internal object AndroidSecurityDiagnostics {
    fun capture(context: Context): SecurityFacts {
        val keyguard = context.getSystemService(Context.KEYGUARD_SERVICE) as? KeyguardManager
        val secureScreenLock = runCatching { keyguard?.isDeviceSecure }.getOrNull()
        val debuggableBuild = runCatching {
            (context.packageManager.getApplicationInfo(context.packageName, 0)
                .flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0
        }.getOrNull()
        return SecurityFacts(
            androidRelease = Build.VERSION.RELEASE.takeUnless(String::isBlank),
            sdkLevel = Build.VERSION.SDK_INT,
            securityPatch = Build.VERSION.SECURITY_PATCH.takeUnless(String::isBlank),
            secureScreenLock = secureScreenLock,
            debuggableBuild = debuggableBuild,
        )
    }
}

internal data class SecurityEvent(val timestamp: Long, val finding: SecurityFinding?)

internal class SecurityEventStore(
    private val readEvents: () -> String?,
    private val writeEvents: (String?) -> Unit,
) {
    constructor(context: Context) : this(
        readEvents = {
            context.getSharedPreferences(PREFERENCES_FILE, Context.MODE_PRIVATE)
                .getString(EVENTS_KEY, "[]")
        },
        writeEvents = { serialized ->
            val preferences = context.getSharedPreferences(PREFERENCES_FILE, Context.MODE_PRIVATE)
            val editor = preferences.edit()
            if (serialized == null) {
                editor.remove(EVENTS_KEY)
            } else {
                editor.putString(EVENTS_KEY, serialized)
            }
            editor.apply()
        },
    )

    fun events(): List<SecurityEvent> = synchronized(lock) {
        runCatching {
            val stored = JSONArray(readEvents() ?: "[]")
            buildList {
                for (index in 0 until stored.length()) {
                    val item = stored.getJSONObject(index)
                    val findingCode = item.optString("finding")
                    val finding = if (findingCode.isEmpty()) {
                        null
                    } else {
                        runCatching { SecurityFinding.valueOf(findingCode) }.getOrNull() ?: continue
                    }
                    add(SecurityEvent(item.getLong("timestamp"), finding))
                }
            }
        }.getOrDefault(emptyList())
    }

    fun recordScan(findings: List<SecurityFinding>): List<SecurityEvent> = synchronized(lock) {
        val current = events().toMutableList()
        val timestamp = System.currentTimeMillis()
        val recordedFindings: List<SecurityFinding?> =
            if (findings.isEmpty()) listOf(null) else findings
        recordedFindings.forEach { current += SecurityEvent(timestamp, it) }
        val recent = current.takeLast(MAX_EVENTS)
        val serialized = JSONArray().apply {
            recent.forEach { event ->
                put(JSONObject().apply {
                    put("timestamp", event.timestamp)
                    put("finding", event.finding?.name.orEmpty())
                })
            }
        }
        writeEvents(serialized.toString())
        recent
    }

    fun clear() {
        synchronized(lock) {
            writeEvents(null)
        }
    }

    private companion object {
        val lock = Any()
        const val PREFERENCES_FILE = "defense_security_events"
        const val EVENTS_KEY = "events"
        const val MAX_EVENTS = 100
    }
}

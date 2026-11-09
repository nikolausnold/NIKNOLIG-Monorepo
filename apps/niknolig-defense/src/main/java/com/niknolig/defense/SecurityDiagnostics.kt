package com.niknolig.defense

import android.app.KeyguardManager
import android.content.Context
import android.content.SharedPreferences
import android.content.pm.ApplicationInfo
import android.os.Build
import org.json.JSONArray
import org.json.JSONObject
import java.util.WeakHashMap

internal object AndroidSecurityDiagnostics {
    fun capture(context: Context): SecurityFacts {
        val keyguard = context.getSystemService(Context.KEYGUARD_SERVICE) as? KeyguardManager
        val supportsSecurityApis = Build.VERSION.SDK_INT >= Build.VERSION_CODES.M
        val secureScreenLock = if (supportsSecurityApis) {
            runCatching { keyguard?.isDeviceSecure }.getOrNull()
        } else {
            null
        }
        val debuggableBuild = runCatching {
            (context.packageManager.getApplicationInfo(context.packageName, 0)
                .flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0
        }.getOrNull()
        return SecurityFacts(
            androidRelease = Build.VERSION.RELEASE.takeUnless(String::isBlank),
            sdkLevel = Build.VERSION.SDK_INT,
            securityPatch = if (supportsSecurityApis) {
                runCatching { Build.VERSION.SECURITY_PATCH.takeUnless(String::isBlank) }.getOrNull()
            } else {
                null
            },
            secureScreenLock = secureScreenLock,
            debuggableBuild = debuggableBuild,
        )
    }
}

internal data class SecurityEvent(val timestamp: Long, val finding: SecurityFinding?)

internal class SecurityEventStore private constructor(
    private val readEvents: () -> String?,
    private val writeEvents: (String?) -> Unit,
    private val lock: Any,
) {
    internal constructor(readEvents: () -> String?, writeEvents: (String?) -> Unit) :
        this(readEvents, writeEvents, Any())

    constructor(context: Context) : this(
        context.getSharedPreferences(PREFERENCES_FILE, Context.MODE_PRIVATE),
    )

    private constructor(preferences: SharedPreferences) : this(
        readEvents = { preferences.getString(EVENTS_KEY, "[]") },
        writeEvents = { serialized ->
            val editor = preferences.edit()
            if (serialized == null) {
                editor.remove(EVENTS_KEY)
            } else {
                editor.putString(EVENTS_KEY, serialized)
            }
            editor.apply()
        },
        lock = lockFor(preferences),
    )

    fun events(): List<SecurityEvent> = synchronized(lock) {
        loadEventsLocked()
    }

    private fun loadEventsLocked(): List<SecurityEvent> {
        val serialized = runCatching { readEvents() ?: "[]" }.getOrElse {
            writeEvents("[]")
            return emptyList()
        }
        val stored = runCatching { JSONArray(serialized) }.getOrElse {
            writeEvents("[]")
            return emptyList()
        }
        return buildList {
            for (index in 0 until stored.length()) {
                val item = stored.optJSONObject(index) ?: continue
                val timestamp = (item.opt("timestamp") as? Number)?.toLong() ?: continue
                val findingCode = item.opt("finding") as? String ?: continue
                val finding = if (findingCode.isEmpty()) {
                    null
                } else {
                    runCatching { SecurityFinding.valueOf(findingCode) }.getOrNull() ?: continue
                }
                add(SecurityEvent(timestamp, finding))
            }
        }
    }

    fun recordScan(findings: List<SecurityFinding>): List<SecurityEvent> = synchronized(lock) {
        val current = loadEventsLocked().toMutableList()
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
        private val locks = WeakHashMap<SharedPreferences, Any>()

        private fun lockFor(preferences: SharedPreferences): Any = synchronized(locks) {
            locks.getOrPut(preferences) { Any() }
        }

        const val PREFERENCES_FILE = "defense_security_events"
        const val EVENTS_KEY = "events"
        const val MAX_EVENTS = 100
    }
}

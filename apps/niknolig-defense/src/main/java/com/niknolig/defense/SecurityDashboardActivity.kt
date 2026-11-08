package com.niknolig.defense

import android.app.Activity
import android.app.AlertDialog
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.ProgressBar
import android.widget.TextView
import java.text.DateFormat
import java.util.Date
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.concurrent.Future

class SecurityDashboardActivity : Activity() {
    private lateinit var factsView: TextView
    private lateinit var findingsView: TextView
    private lateinit var eventsView: TextView
    private lateinit var scanButton: Button
    private lateinit var progress: ProgressBar
    private lateinit var eventStore: SecurityEventStore
    private val scanExecutor: ExecutorService = Executors.newSingleThreadExecutor()
    private var scanTask: Future<*>? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_security_dashboard)
        factsView = findViewById(R.id.security_facts)
        findingsView = findViewById(R.id.security_findings)
        eventsView = findViewById(R.id.security_events)
        scanButton = findViewById(R.id.security_scan_button)
        progress = findViewById(R.id.security_scan_progress)
        eventStore = SecurityEventStore(this)

        findViewById<Button>(R.id.security_clear_events_button).setOnClickListener {
            AlertDialog.Builder(this)
                .setTitle(R.string.security_clear_events_title)
                .setMessage(R.string.security_clear_events_confirmation)
                .setNegativeButton(android.R.string.cancel, null)
                .setPositiveButton(R.string.security_clear_events_action) { _, _ ->
                    eventStore.clear()
                    showEvents(emptyList())
                }
                .show()
        }
        findViewById<Button>(R.id.security_dashboard_close_button).setOnClickListener { finish() }
        scanButton.setOnClickListener { runScan() }
        showEvents(eventStore.events())
    }

    override fun onDestroy() {
        scanTask?.cancel(true)
        scanExecutor.shutdownNow()
        super.onDestroy()
    }

    private fun runScan() {
        scanButton.isEnabled = false
        progress.visibility = View.VISIBLE
        findingsView.setText(R.string.security_scan_loading)
        scanTask = scanExecutor.submit {
            val result = runCatching {
                val facts = AndroidSecurityDiagnostics.capture(this)
                val findings = SecurityAssessment.findings(facts)
                eventStore.recordScan(findings)
                Pair(facts, findings)
            }
            runOnUiThread {
                if (isFinishing || isDestroyed) return@runOnUiThread
                scanButton.isEnabled = true
                progress.visibility = View.GONE
                result.onSuccess { (facts, findings) ->
                    factsView.text = getString(
                        R.string.security_facts_format,
                        facts.androidRelease ?: getString(R.string.security_unknown),
                        facts.sdkLevel?.toString() ?: getString(R.string.security_unknown),
                        facts.securityPatch ?: getString(R.string.security_unknown),
                        getString(if (facts.secureScreenLock == true) {
                            R.string.security_enabled
                        } else if (facts.secureScreenLock == false) {
                            R.string.security_disabled
                        } else {
                            R.string.security_unknown
                        }),
                        getString(if (facts.debuggableBuild == true) {
                            R.string.security_yes
                        } else if (facts.debuggableBuild == false) {
                            R.string.security_no
                        } else {
                            R.string.security_unknown
                        }),
                    )
                    findingsView.text = if (findings.isEmpty()) {
                        getString(R.string.security_no_findings)
                    } else {
                        findings.joinToString("\n") { getString(it.messageResource()) }
                    }
                    showEvents(eventStore.events())
                }
                result.onFailure {
                    findingsView.setText(R.string.security_scan_failed)
                }
            }
        }
    }

    private fun showEvents(events: List<SecurityEvent>) {
        eventsView.text = if (events.isEmpty()) {
            getString(R.string.security_events_empty)
        } else {
            events.asReversed().joinToString("\n\n") { event ->
                val label = event.finding?.let { getString(it.messageResource()) }
                    ?: getString(R.string.security_scan_completed)
                "${DateFormat.getDateTimeInstance().format(Date(event.timestamp))}: $label"
            }
        }
    }

    private fun SecurityFinding.messageResource(): Int = when (this) {
        SecurityFinding.NO_SECURE_SCREEN_LOCK -> R.string.security_finding_no_lock
        SecurityFinding.SCREEN_LOCK_STATE_UNKNOWN -> R.string.security_finding_lock_unknown
        SecurityFinding.DEBUGGABLE_BUILD -> R.string.security_finding_debug_build
        SecurityFinding.BUILD_STATE_UNKNOWN -> R.string.security_finding_build_unknown
        SecurityFinding.SECURITY_PATCH_UNKNOWN -> R.string.security_finding_patch_unknown
    }
}

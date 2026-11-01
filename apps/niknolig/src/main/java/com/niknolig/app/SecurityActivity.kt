package com.niknolig.app

import android.app.Activity
import android.os.Build
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast

class SecurityActivity : Activity() {
    private val log by lazy { connectionLog() }
    private lateinit var content: LinearLayout

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_security)
        content = findViewById(R.id.security_content)
        findViewById<Button>(R.id.security_close_button).setOnClickListener { finish() }
        findViewById<Button>(R.id.security_clear_log_button).setOnClickListener {
            val cleared = runCatching { log.clear() }.getOrDefault(false)
            Toast.makeText(
                this,
                if (cleared) R.string.security_log_cleared else R.string.security_log_clear_failed,
                Toast.LENGTH_LONG,
            ).show()
            render()
        }
        render()
    }

    private fun render() {
        val overview = SecurityOverview.build(runtimeSecurityChecks(), log.state(), PairingGate.evaluate())
        content.removeAllViews()

        section(R.string.security_events_heading)
        if (overview.events.isEmpty()) {
            body(getString(R.string.security_events_none))
        } else {
            overview.events.forEach {
                body(getString(R.string.security_event_line, formatTime(it.timeMillis), getString(it.code.labelRes())))
            }
        }

        section(R.string.security_checks_heading)
        overview.failedChecks.forEach {
            body(getString(R.string.security_check_failed, getString(it.labelRes())))
        }
        overview.passedChecks.forEach {
            body(getString(R.string.security_check_passed, getString(it.labelRes())))
        }

        section(R.string.security_blockers_heading)
        if (overview.blockers.isEmpty()) body(getString(R.string.security_blockers_none))
        overview.blockers.forEach { body("• " + getString(it.messageRes())) }

        section(R.string.security_hints_heading)
        body(getString(R.string.security_hint_no_monitoring))
        body(getString(R.string.security_hint_no_secrets))
        body(getString(R.string.security_hint_local))
    }

    private fun section(heading: Int) {
        content.addView(TextView(this).apply {
            setText(heading)
            if (Build.VERSION.SDK_INT >= 28) isAccessibilityHeading = true
            setTextColor(getColor(R.color.gold))
            textSize = 14f
            setTypeface(typeface, android.graphics.Typeface.BOLD)
            layoutParams = params(resources.getDimensionPixelSize(R.dimen.space_large))
        })
    }

    private fun body(text: String): View = TextView(this).apply {
        this.text = text
        setTextColor(getColor(R.color.text_primary))
        textSize = 16f
        layoutParams = params(resources.getDimensionPixelSize(R.dimen.space_small))
    }.also { content.addView(it) }

    private fun params(topMargin: Int) = LinearLayout.LayoutParams(
        LinearLayout.LayoutParams.MATCH_PARENT,
        LinearLayout.LayoutParams.WRAP_CONTENT,
    ).apply { this.topMargin = topMargin }
}

private fun ConnectionCode.labelRes(): Int = when (this) {
    ConnectionCode.TIMED_OUT -> R.string.connection_code_timed_out
    ConnectionCode.NETWORK_ERROR -> R.string.connection_code_network_error
    ConnectionCode.INVALID_RESPONSE -> R.string.connection_code_invalid_response
    ConnectionCode.HTTP_ERROR -> R.string.connection_code_http_error
    ConnectionCode.READY, ConnectionCode.NOT_CONFIGURED -> R.string.connection_code_other
}

private fun SecurityCheckId.labelRes(): Int = when (this) {
    SecurityCheckId.BACKUP_DISABLED -> R.string.security_check_backup
    SecurityCheckId.CLEARTEXT_BLOCKED -> R.string.security_check_cleartext
    SecurityCheckId.NOT_DEBUGGABLE -> R.string.security_check_debuggable
    SecurityCheckId.BACKEND_HTTPS -> R.string.security_check_https
    SecurityCheckId.ONLY_INTERNET_PERMISSION -> R.string.security_check_permissions
}

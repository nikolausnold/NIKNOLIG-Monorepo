package com.niknolig.app

import android.app.Activity
import android.app.AlertDialog
import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.TextView
import android.widget.Toast

class SupportActivity : Activity() {
    private var backendStatus: Int? = null
    private lateinit var checkButton: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_support)

        backendStatus = savedInstanceState?.getInt("backendStatus")?.takeIf { it != 0 }
        checkButton = findViewById(R.id.support_check_ai)
        showSupportState()

        checkButton.setOnClickListener { checkBackend() }
        findViewById<Button>(R.id.support_escalate).setOnClickListener {
            if (backendStatus != null) {
                AlertDialog.Builder(this)
                    .setTitle(R.string.support_escalation_title)
                    .setMessage(getString(R.string.support_escalation_consent, getString(R.string.support_email)))
                    .setNegativeButton(android.R.string.cancel, null)
                    .setPositiveButton(R.string.support_email_draft) { _, _ ->
                        openEmailDraft()
                    }
                    .show()
            }
        }
        findViewById<Button>(R.id.support_close).setOnClickListener { finish() }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        outState.putInt("backendStatus", backendStatus ?: 0)
        super.onSaveInstanceState(outState)
    }

    private fun showSupportState() {
        findViewById<TextView>(R.id.support_ai_status).setText(
            backendStatus ?: R.string.support_ai_not_checked
        )
        findViewById<Button>(R.id.support_escalate).visibility =
            if (backendStatus != null) View.VISIBLE else View.GONE
        checkButton.visibility = if (backendStatus != null) View.GONE else View.VISIBLE
    }

    private fun checkBackend() {
        checkButton.isEnabled = false
        findViewById<TextView>(R.id.support_ai_status)
            .setText(R.string.support_backend_checking)
        Thread({
            val result = BackendHealthClient(BuildConfig.BACKEND_BASE_URL).check()
            val message = when (result) {
                BackendHealthResult.Ready -> R.string.support_backend_ready
                BackendHealthResult.NotConfigured -> R.string.support_backend_not_configured
                BackendHealthResult.InvalidResponse -> R.string.support_backend_invalid_response
                BackendHealthResult.TimedOut -> R.string.support_backend_timeout
                BackendHealthResult.NetworkError -> R.string.support_backend_network_error
                is BackendHealthResult.HttpError -> R.string.support_backend_http_error
            }
            runOnUiThread {
                if (!isFinishing && !isDestroyed) {
                    backendStatus = message
                    checkButton.isEnabled = true
                    showSupportState()
                }
            }
        }, "niknolig-backend-health").start()
    }

    private fun openEmailDraft() {
        if (backendStatus == null) return
        val emailIntent = Intent(Intent.ACTION_SENDTO).apply {
            data = Uri.parse(
                "mailto:${Uri.encode(getString(R.string.support_email), "@")}" +
                    "?subject=${Uri.encode(getString(R.string.support_email_subject))}" +
                    "&body=${Uri.encode(getString(R.string.support_email_body))}"
            )
        }
        try {
            startActivity(emailIntent)
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(
                this,
                getString(R.string.support_email_manual, getString(R.string.support_email)),
                Toast.LENGTH_LONG,
            ).show()
        }
    }
}

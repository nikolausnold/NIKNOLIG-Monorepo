package com.niknolig.defense

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
    private var aiUnavailable = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_support)

        aiUnavailable = savedInstanceState?.getBoolean("aiUnavailable") ?: false
        showSupportState()

        findViewById<Button>(R.id.support_check_ai).setOnClickListener {
            // No AI endpoint is configured; do not simulate an answer or send data.
            aiUnavailable = true
            showSupportState()
        }
        findViewById<Button>(R.id.support_escalate).setOnClickListener {
            if (aiUnavailable) {
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
        outState.putBoolean("aiUnavailable", aiUnavailable)
        super.onSaveInstanceState(outState)
    }

    private fun showSupportState() {
        findViewById<TextView>(R.id.support_ai_status).setText(
            if (aiUnavailable) R.string.support_ai_unavailable else R.string.support_ai_not_checked
        )
        findViewById<Button>(R.id.support_escalate).visibility =
            if (aiUnavailable) View.VISIBLE else View.GONE
        findViewById<Button>(R.id.support_check_ai).visibility =
            if (aiUnavailable) View.GONE else View.VISIBLE
    }

    private fun openEmailDraft() {
        if (!aiUnavailable) return
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

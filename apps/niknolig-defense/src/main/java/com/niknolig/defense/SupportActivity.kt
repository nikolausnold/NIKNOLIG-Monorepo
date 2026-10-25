package com.niknolig.defense

import android.app.Activity
import android.app.AlertDialog
import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import org.niknolig.support.AnswerCode
import org.niknolig.support.BackendDiagnostic
import org.niknolig.support.SupportApp
import org.niknolig.support.SupportAssistant
import org.niknolig.support.SupportEscalationQueue
import org.niknolig.support.SupportPayloadCipher

class SupportActivity : Activity() {
    private var backendStatus: Int? = null
    private lateinit var checkButton: Button
    private lateinit var liveButton: Button
    private lateinit var questionInput: EditText
    private lateinit var answerView: TextView
    private lateinit var payloadCipher: SupportPayloadCipher
    private var supportQueue: SupportEscalationQueue? = null
    private var pendingTicketId: String? = null
    private var lastDiagnostic = "AI_DISABLED"
    private var lastQuestion: String? = null
    private var questionRequestKey = java.util.UUID.randomUUID().toString()
    private val manualRequestKey = "MANUAL_${java.util.UUID.randomUUID()}"
    private val supportApp = SupportApp.NIKNOLIG_DEFENSE

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_support)

        backendStatus = savedInstanceState?.getInt("backendStatus")?.takeIf { it != 0 }
        supportQueue = runCatching {
            SupportEscalationQueue(AndroidSupportTicketStore(this))
        }.getOrNull()
        payloadCipher = AndroidSupportPayloadCipher()
        checkButton = findViewById(R.id.support_check_ai)
        liveButton = findViewById(R.id.support_check_live)
        questionInput = findViewById(R.id.support_question)
        answerView = findViewById(R.id.support_answer_result)
        showSupportState()

        checkButton.setOnClickListener { checkBackend() }
        liveButton.setOnClickListener { checkBackend(BackendHealthEndpoint.LIVE) }
        findViewById<Button>(R.id.support_answer).setOnClickListener { answerQuestion() }
        findViewById<Button>(R.id.support_escalate).setOnClickListener {
            AlertDialog.Builder(this)
                .setTitle(R.string.support_escalation_title)
                .setMessage(getString(R.string.support_escalation_consent, getString(R.string.support_email)))
                .setNegativeButton(android.R.string.cancel, null)
                .setPositiveButton(R.string.support_email_draft) { _, _ ->
                    openEmailDraft()
                }
                .show()
        }
        findViewById<Button>(R.id.support_mark_sent).setOnClickListener {
            val ticketId = pendingTicketId
            if (ticketId != null && supportQueue?.complete(ticketId) == true) {
                pendingTicketId = null
                refreshQueueState()
                answerView.visibility = View.VISIBLE
                answerView.setText(R.string.support_ticket_marked_sent)
            }
        }
        findViewById<Button>(R.id.support_close).setOnClickListener { finish() }
        findViewById<Button>(R.id.support_website).setOnClickListener { openOfficialWebsite() }
        findViewById<Button>(R.id.support_delete_ticket).setOnClickListener {
            val ticketId = pendingTicketId ?: return@setOnClickListener
            if (runCatching { supportQueue?.remove(ticketId, supportApp) }.getOrNull() == true) {
                pendingTicketId = null
                questionInput.text.clear()
                lastQuestion = null
                refreshQueueState()
                answerView.visibility = View.VISIBLE
                answerView.setText(R.string.support_ticket_deleted)
            } else {
                Toast.makeText(this, R.string.support_ticket_delete_failed, Toast.LENGTH_LONG).show()
            }
        }
        refreshQueueState()
    }

    override fun onSaveInstanceState(outState: Bundle) {
        outState.putInt("backendStatus", backendStatus ?: 0)
        super.onSaveInstanceState(outState)
    }

    private fun showSupportState() {
        findViewById<TextView>(R.id.support_ai_status).setText(
            backendStatus ?: R.string.support_ai_unavailable
        )
        checkButton.visibility = View.VISIBLE
    }

    private fun answerQuestion() {
        val question = questionInput.text.toString()
        if (question.isBlank()) {
            answerView.visibility = View.VISIBLE
            answerView.setText(R.string.support_answer_empty)
            return
        }
        val answer = SupportAssistant.answer(question)
        answerView.visibility = View.VISIBLE
        val answerResource = when (answer.code) {
            AnswerCode.BACKEND_HEALTH -> R.string.support_answer_backend
            AnswerCode.PRIVACY -> R.string.support_answer_privacy
            AnswerCode.PAYMENT -> R.string.support_answer_payment
            AnswerCode.TROUBLESHOOTING -> R.string.support_answer_troubleshooting
            AnswerCode.ACCOUNT_UNAVAILABLE -> R.string.support_answer_account
            AnswerCode.UNRESOLVED -> R.string.support_answer_unresolved
        }
        answerView.setText(answerResource)
        if (answer.escalationRequired) {
            val encrypted = runCatching { payloadCipher.encrypt(question) }.getOrNull()
            if (encrypted == null) {
                findViewById<TextView>(R.id.support_queue_status).apply {
                    visibility = View.VISIBLE
                    setText(R.string.support_queue_unavailable)
                }
            } else {
                ensureTicket(answer.code.name, "UNRESOLVED", questionRequestKey(question), encrypted)
            }
        }
    }

    private fun checkBackend(endpoint: BackendHealthEndpoint = BackendHealthEndpoint.READY) {
        checkButton.isEnabled = false
        liveButton.isEnabled = false
        findViewById<TextView>(R.id.support_ai_status)
            .setText(R.string.support_backend_checking)
        Thread({
            val result = BackendHealthClient(BuildConfig.BACKEND_BASE_URL).check(endpoint)
            val message = when (result) {
                BackendHealthResult.Live -> R.string.support_backend_live
                BackendHealthResult.Ready -> R.string.support_backend_ready
                BackendHealthResult.NotConfigured -> R.string.support_backend_not_configured
                BackendHealthResult.InvalidResponse -> R.string.support_backend_invalid_response
                BackendHealthResult.TimedOut -> R.string.support_backend_timeout
                BackendHealthResult.NetworkError -> R.string.support_backend_network_error
                is BackendHealthResult.HttpError -> R.string.support_backend_http_error
            }
            val diagnostic = when (result) {
                BackendHealthResult.Live -> BackendDiagnostic.LIVE
                BackendHealthResult.Ready -> BackendDiagnostic.READY
                BackendHealthResult.NotConfigured -> BackendDiagnostic.NOT_CONFIGURED
                BackendHealthResult.InvalidResponse -> BackendDiagnostic.INVALID_RESPONSE
                BackendHealthResult.TimedOut -> BackendDiagnostic.TIMED_OUT
                BackendHealthResult.NetworkError -> BackendDiagnostic.NETWORK_ERROR
                is BackendHealthResult.HttpError -> BackendDiagnostic.HTTP_ERROR
            }
            runOnUiThread {
                if (!isFinishing && !isDestroyed) {
                    backendStatus = message
                    lastDiagnostic = diagnostic.name
                    checkButton.isEnabled = true
                    liveButton.isEnabled = true
                    showSupportState()
                    if (SupportAssistant.diagnose(diagnostic).escalationRequired) {
                        val encrypted = runCatching { payloadCipher.encrypt("") }.getOrNull()
                        if (encrypted != null) {
                            ensureTicket(
                                "BACKEND",
                                diagnostic.name,
                                "BACKEND_${diagnostic.name}",
                                encrypted,
                            )
                        }
                    }
                }
            }
        }, "niknolig-defense-backend-health").start()
    }

    private fun questionRequestKey(question: String): String {
        if (lastQuestion != question) {
            lastQuestion = question
            questionRequestKey = java.util.UUID.randomUUID().toString()
        }
        return questionRequestKey
    }

    private fun ensureTicket(
        issueCode: String,
        diagnosticCode: String,
        requestKey: String,
        encryptedPayload: String,
    ): String? {
        val ticket = runCatching {
            supportQueue?.enqueue(supportApp, requestKey, issueCode, diagnosticCode, encryptedPayload)
        }.getOrNull()
        if (ticket == null) {
            val queueStatus = findViewById<TextView>(R.id.support_queue_status)
            queueStatus.visibility = View.VISIBLE
            queueStatus.setText(R.string.support_queue_unavailable)
            return null
        }
        pendingTicketId = ticket.id
        refreshQueueState()
        return ticket.id
    }

    private fun refreshQueueState() {
        val tickets = runCatching { supportQueue?.pending().orEmpty() }.getOrDefault(emptyList())
        val ticket = tickets.lastOrNull { it.app == supportApp }
        pendingTicketId = ticket?.id
        val queueStatus = findViewById<TextView>(R.id.support_queue_status)
        if (ticket != null) {
            queueStatus.visibility = View.VISIBLE
            queueStatus.text = getString(
                when (ticket.handoffState.name) {
                    "HANDED_OFF" -> R.string.support_ticket_handed_off
                    "UNCERTAIN" -> R.string.support_ticket_handoff_uncertain
                    else -> R.string.support_ticket_queued
                },
                ticket.id,
            )
        } else if (supportQueue != null) {
            queueStatus.visibility = View.GONE
        }
        findViewById<Button>(R.id.support_mark_sent).visibility =
            if (ticket?.handoffState?.name == "HANDED_OFF") View.VISIBLE else View.GONE
        findViewById<Button>(R.id.support_delete_ticket).visibility =
            if (ticket != null) View.VISIBLE else View.GONE
    }

    private fun openEmailDraft() {
        var ticket = pendingTicketId?.let { id ->
            runCatching { supportQueue?.pending()?.firstOrNull { it.id == id } }.getOrNull()
        }
        if (ticket == null) {
            val encrypted = runCatching { payloadCipher.encrypt(questionInput.text.toString()) }.getOrNull()
            val id = encrypted?.let {
                ensureTicket("MANUAL_REQUEST", lastDiagnostic, manualRequestKey, it)
            } ?: run {
                Toast.makeText(
                    this,
                    getString(R.string.support_email_manual, getString(R.string.support_email)),
                    Toast.LENGTH_LONG,
                ).show()
                return
            }
            ticket = supportQueue?.pending()?.firstOrNull { it.id == id }
        }
        val currentTicket = ticket ?: return
        if (currentTicket.handoffState.name != "READY") {
            Toast.makeText(
                this,
                if (currentTicket.handoffState.name == "HANDED_OFF") {
                    R.string.support_ticket_already_handed_off
                } else {
                    R.string.support_ticket_handoff_uncertain
                },
                Toast.LENGTH_LONG,
            ).show()
            return
        }
        if (!currentTicket.canShareMetadata(supportApp)) {
            Toast.makeText(this, R.string.support_queue_unavailable, Toast.LENGTH_LONG).show()
            return
        }
        val started = runCatching {
            supportQueue?.beginHandoff(currentTicket.id)
        }.getOrNull()
        if (started == null) {
            val message = if (currentTicket.handoffAttempts >= 3) {
                getString(
                    R.string.support_ticket_handoff_limit,
                    getString(R.string.support_email),
                    currentTicket.id,
                )
            } else {
                getString(R.string.support_queue_unavailable)
            }
            Toast.makeText(this, message, Toast.LENGTH_LONG).show()
            return
        }
        val emailIntent = Intent(Intent.ACTION_SENDTO).apply {
            data = Uri.parse(
                "mailto:${Uri.encode(getString(R.string.support_email), "@")}" +
                    "?subject=${Uri.encode(getString(R.string.support_email_subject, started.id))}" +
                    "&body=${Uri.encode(getString(
                        R.string.support_email_body,
                        started.id,
                        supportApp.value,
                        started.issueCode,
                        started.diagnosticCode,
                    ))}"
            )
        }
        try {
            startActivity(emailIntent)
            runCatching { supportQueue?.finishHandoff(started.id, launched = true) }
            refreshQueueState()
            Toast.makeText(this, R.string.support_ticket_handoff_done, Toast.LENGTH_LONG).show()
        } catch (_: ActivityNotFoundException) {
            runCatching { supportQueue?.finishHandoff(started.id, launched = false) }
            Toast.makeText(
                this,
                R.string.support_ticket_handoff_failed,
                Toast.LENGTH_LONG,
            ).show()
        } catch (_: SecurityException) {
            runCatching { supportQueue?.finishHandoff(started.id, launched = false) }
            Toast.makeText(this, R.string.support_ticket_handoff_failed, Toast.LENGTH_LONG).show()
        }
    }

    private fun openOfficialWebsite() {
        try {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(getString(R.string.official_website_url))))
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(this, R.string.support_website_unavailable, Toast.LENGTH_LONG).show()
        } catch (_: SecurityException) {
            Toast.makeText(this, R.string.support_website_unavailable, Toast.LENGTH_LONG).show()
        }
    }
}

package com.niknolig.app

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import org.niknolig.support.EscalationTicket
import org.niknolig.support.HandoffState
import org.niknolig.support.SupportApp
import org.niknolig.support.SupportTicketStore
import java.util.UUID

internal class AndroidSupportTicketStore(context: Context) : SupportTicketStore {
    private val preferences = context.getSharedPreferences("support_queue", Context.MODE_PRIVATE)

    override fun load(): List<EscalationTicket> {
        val encoded = preferences.getString(KEY_TICKETS, null) ?: return emptyList()
        return try {
            val records = JSONArray(encoded)
            (0 until records.length()).map { index ->
                val record = records.getJSONObject(index)
                val ticket = EscalationTicket(
                    id = record.getString("id"),
                    app = SupportApp.valueOf(record.getString("app")),
                    requestKey = record.getString("requestKey"),
                    issueCode = record.getString("issue"),
                    diagnosticCode = record.getString("diagnostic"),
                    encryptedPayload = record.getString("payload"),
                    createdAtMillis = record.getLong("created"),
                    handoffAttempts = record.getInt("attempts"),
                    handoffState = HandoffState.valueOf(record.getString("state")),
                )
                require(ticket.app == SupportApp.NIKNOLIG)
                require(runCatching { UUID.fromString(ticket.id).toString() == ticket.id }.getOrDefault(false))
                require(ticket.requestKey.matches(REQUEST_KEY_PATTERN))
                require(ticket.issueCode.matches(CODE_PATTERN))
                require(ticket.diagnosticCode.matches(CODE_PATTERN))
                require(ticket.encryptedPayload.matches(ENCRYPTED_PAYLOAD_PATTERN))
                require(ticket.handoffAttempts in 0..3)
                ticket
            }
        } catch (error: Exception) {
            throw IllegalStateException("Stored support queue is invalid", error)
        }
    }

    override fun save(tickets: List<EscalationTicket>) {
        require(tickets.size <= 20 && tickets.all { it.app == SupportApp.NIKNOLIG })
        val records = JSONArray()
        tickets.forEach { ticket ->
            records.put(
                JSONObject()
                    .put("id", ticket.id)
                    .put("app", ticket.app.name)
                    .put("requestKey", ticket.requestKey)
                    .put("issue", ticket.issueCode)
                    .put("diagnostic", ticket.diagnosticCode)
                    .put("payload", ticket.encryptedPayload)
                    .put("created", ticket.createdAtMillis)
                    .put("attempts", ticket.handoffAttempts)
                    .put("state", ticket.handoffState.name),
            )
        }
        check(preferences.edit().putString(KEY_TICKETS, records.toString()).commit()) {
            "Support queue could not be persisted"
        }
    }

    private companion object {
        const val KEY_TICKETS = "tickets"
        val CODE_PATTERN = Regex("[A-Z0-9_]{1,48}")
        val REQUEST_KEY_PATTERN = Regex("[A-Za-z0-9_-]{1,128}")
        val ENCRYPTED_PAYLOAD_PATTERN = Regex("[A-Za-z0-9_+/=-]{1,8192}")
    }
}

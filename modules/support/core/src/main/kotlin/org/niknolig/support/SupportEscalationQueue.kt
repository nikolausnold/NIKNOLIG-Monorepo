package org.niknolig.support

import java.util.UUID

enum class SupportApp(val value: String) {
    NIKNOLIG("niknolig"),
    NIKNOLIG_DEFENSE("niknolig-defense"),
}

enum class HandoffState {
    READY,
    UNCERTAIN,
    HANDED_OFF,
}

data class EscalationTicket(
    val id: String,
    val app: SupportApp,
    val requestKey: String,
    val issueCode: String,
    val diagnosticCode: String,
    val encryptedPayload: String,
    val createdAtMillis: Long,
    val handoffAttempts: Int = 0,
    val handoffState: HandoffState = HandoffState.READY,
) {
    fun canShareMetadata(expectedApp: SupportApp): Boolean =
        app == expectedApp &&
            runCatching { UUID.fromString(id).toString() == id }.getOrDefault(false) &&
            issueCode in (AnswerCode.entries.map { it.name } + listOf("BACKEND", "MANUAL_REQUEST")) &&
            diagnosticCode in (BackendDiagnostic.entries.map { it.name } +
                listOf("AI_DISABLED", "UNRESOLVED", "NO_MATCH"))
}

interface SupportTicketStore {
    fun load(): List<EscalationTicket>
    fun save(tickets: List<EscalationTicket>)
}

interface SupportPayloadCipher {
    fun encrypt(plaintext: String): String
    fun decrypt(ciphertext: String): String
}

class SupportEscalationQueue(
    private val store: SupportTicketStore,
    private val clock: () -> Long = System::currentTimeMillis,
    private val idGenerator: () -> String = { UUID.randomUUID().toString() },
    private val maxHandoffAttempts: Int = 3,
) {
    init {
        require(maxHandoffAttempts in 1..5)
    }

    @Synchronized
    fun enqueue(
        app: SupportApp,
        requestKey: String,
        issueCode: String,
        diagnosticCode: String,
        encryptedPayload: String,
    ): EscalationTicket {
        require(requestKey.matches(REQUEST_KEY_PATTERN))
        require(issueCode.matches(CODE_PATTERN) && diagnosticCode.matches(CODE_PATTERN))
        require(encryptedPayload.matches(ENCRYPTED_PAYLOAD_PATTERN))
        val tickets = store.load()
        tickets.firstOrNull {
            it.app == app && it.requestKey == requestKey
        }?.let { return it }
        require(tickets.size < MAX_TICKETS) { "Support queue is full" }
        val ticket = EscalationTicket(
            id = idGenerator(),
            app = app,
            requestKey = requestKey,
            issueCode = issueCode,
            diagnosticCode = diagnosticCode,
            encryptedPayload = encryptedPayload,
            createdAtMillis = clock(),
        )
        require(runCatching { UUID.fromString(ticket.id).toString() == ticket.id }.getOrDefault(false))
        store.save(tickets + ticket)
        return ticket
    }

    @Synchronized
    fun pending(): List<EscalationTicket> = store.load()

    @Synchronized
    fun beginHandoff(ticketId: String): EscalationTicket? {
        val tickets = store.load()
        val ticket = tickets.firstOrNull { it.id == ticketId } ?: return null
        if (ticket.handoffState != HandoffState.READY ||
            ticket.handoffAttempts >= maxHandoffAttempts
        ) {
            return null
        }
        return ticket.copy(
            handoffAttempts = ticket.handoffAttempts + 1,
            handoffState = HandoffState.UNCERTAIN,
        ).also { updated ->
            store.save(tickets.map { if (it.id == ticketId) updated else it })
        }
    }

    @Synchronized
    fun finishHandoff(ticketId: String, launched: Boolean): EscalationTicket? {
        val tickets = store.load()
        val ticket = tickets.firstOrNull { it.id == ticketId } ?: return null
        if (ticket.handoffState != HandoffState.UNCERTAIN) return null
        return ticket.copy(
            handoffState = if (launched) HandoffState.HANDED_OFF else HandoffState.READY,
        ).also { updated ->
            store.save(tickets.map { if (it.id == ticketId) updated else it })
        }
    }

    @Synchronized
    fun complete(ticketId: String): Boolean {
        val tickets = store.load()
        if (tickets.none { it.id == ticketId && it.handoffState == HandoffState.HANDED_OFF }) {
            return false
        }
        store.save(tickets.filterNot { it.id == ticketId })
        return true
    }

    @Synchronized
    fun remove(ticketId: String, app: SupportApp): Boolean {
        val tickets = store.load()
        val remaining = tickets.filterNot { it.id == ticketId && it.app == app }
        if (remaining.size == tickets.size) return false
        store.save(remaining)
        return true
    }

    companion object {
        const val MAX_TICKETS = 20
        private val CODE_PATTERN = Regex("[A-Z0-9_]{1,48}")
        private val REQUEST_KEY_PATTERN = Regex("[A-Za-z0-9_-]{1,128}")
        private val ENCRYPTED_PAYLOAD_PATTERN = Regex("[A-Za-z0-9_+/=-]{1,8192}")
    }
}

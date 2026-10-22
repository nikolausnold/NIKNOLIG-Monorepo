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
    val issueCode: String,
    val diagnosticCode: String,
    val createdAtMillis: Long,
    val handoffAttempts: Int = 0,
    val handoffState: HandoffState = HandoffState.READY,
)

interface SupportTicketStore {
    fun load(): List<EscalationTicket>
    fun save(tickets: List<EscalationTicket>)
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
    fun enqueue(app: SupportApp, issueCode: String, diagnosticCode: String): EscalationTicket {
        require(issueCode.matches(CODE_PATTERN) && diagnosticCode.matches(CODE_PATTERN))
        val tickets = store.load()
        tickets.firstOrNull {
            it.app == app && it.issueCode == issueCode &&
                it.diagnosticCode == diagnosticCode
        }?.let { return it }
        require(tickets.size < MAX_TICKETS) { "Support queue is full" }
        val ticket = EscalationTicket(
            id = idGenerator(),
            app = app,
            issueCode = issueCode,
            diagnosticCode = diagnosticCode,
            createdAtMillis = clock(),
        )
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
        if (tickets.none { it.id == ticketId }) return false
        store.save(tickets.filterNot { it.id == ticketId })
        return true
    }

    companion object {
        const val MAX_TICKETS = 20
        private val CODE_PATTERN = Regex("[A-Z0-9_]{1,48}")
    }
}

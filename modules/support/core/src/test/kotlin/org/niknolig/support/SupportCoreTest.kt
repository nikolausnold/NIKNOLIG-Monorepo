package org.niknolig.support

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class SupportCoreTest {
    @Test
    fun commonQuestionsReceiveDeterministicAnswers() {
        assertEquals(AnswerCode.BACKEND_HEALTH, SupportAssistant.answer("Wie prüfe ich die Verbindung?").code)
        assertEquals(AnswerCode.PRIVACY, SupportAssistant.answer("Was passiert mit meinen Daten?").code)
        assertEquals(AnswerCode.PAYMENT, SupportAssistant.answer("Frage zur Zahlung").code)
        assertEquals(AnswerCode.TROUBLESHOOTING, SupportAssistant.answer("Die App funktioniert nicht").code)
    }

    @Test
    fun unknownAndUnavailableAccountQuestionsRequestHumanSupport() {
        assertTrue(SupportAssistant.answer("Wie setze ich mein Passwort zurück?").escalationRequired)
        assertTrue(SupportAssistant.answer("Bitte prüft meinen besonderen Fehler").escalationRequired)
        assertTrue(SupportAssistant.answer(" ").escalationRequired)
        assertTrue(SupportAssistant.answer("é".repeat(1_025)).escalationRequired)
    }

    @Test
    fun backendDiagnosticsOnlyEscalateWhenHealthCheckFailed() {
        assertFalse(SupportAssistant.diagnose(BackendDiagnostic.READY).escalationRequired)
        BackendDiagnostic.entries.filter { it != BackendDiagnostic.READY }.forEach {
            assertTrue(SupportAssistant.diagnose(it).escalationRequired)
        }
    }

    @Test
    fun queueIsIdempotentScopedAndPersistsOnlyTypedMetadata() {
        val store = MemoryTicketStore()
        val queue = SupportEscalationQueue(store, clock = { 42L }, idGenerator = { "ticket-1" })
        val first = queue.enqueue(SupportApp.NIKNOLIG, "UNRESOLVED", "NO_MATCH")
        val duplicate = queue.enqueue(SupportApp.NIKNOLIG, "UNRESOLVED", "NO_MATCH")
        val defense = queue.enqueue(SupportApp.NIKNOLIG_DEFENSE, "UNRESOLVED", "NO_MATCH")

        assertEquals(first, duplicate)
        assertEquals(42L, first.createdAtMillis)
        assertEquals("ticket-1", first.id)
        assertEquals(2, queue.pending().size)
        assertFalse(store.toString().contains("customer text"))
        assertEquals(SupportApp.NIKNOLIG_DEFENSE, defense.app)
    }

    @Test
    fun failedHandoffIsRetainedAndRetriesAreBounded() {
        val store = MemoryTicketStore()
        val queue = SupportEscalationQueue(store, idGenerator = { "ticket-1" }, maxHandoffAttempts = 2)
        val ticket = queue.enqueue(SupportApp.NIKNOLIG, "BACKEND", "NETWORK_ERROR")

        assertEquals(HandoffState.UNCERTAIN, queue.beginHandoff(ticket.id)?.handoffState)
        assertEquals(HandoffState.READY, queue.finishHandoff(ticket.id, launched = false)?.handoffState)
        assertEquals(1, queue.pending().single().handoffAttempts)
        assertEquals(HandoffState.UNCERTAIN, queue.beginHandoff(ticket.id)?.handoffState)
        assertEquals(HandoffState.READY, queue.finishHandoff(ticket.id, launched = false)?.handoffState)
        assertNull(queue.beginHandoff(ticket.id))
        assertEquals(1, queue.pending().size)
    }

    @Test
    fun successfulHandoffCannotBeRetriedAndCanBeCompletedByUser() {
        val queue = SupportEscalationQueue(MemoryTicketStore(), idGenerator = { "ticket-1" })
        val ticket = queue.enqueue(SupportApp.NIKNOLIG_DEFENSE, "UNRESOLVED", "NO_MATCH")

        queue.beginHandoff(ticket.id)
        assertEquals(HandoffState.HANDED_OFF, queue.finishHandoff(ticket.id, launched = true)?.handoffState)
        assertNull(queue.beginHandoff(ticket.id))
        assertTrue(queue.complete(ticket.id))
        assertTrue(queue.pending().isEmpty())
    }

    private class MemoryTicketStore : SupportTicketStore {
        private var tickets = emptyList<EscalationTicket>()
        override fun load() = tickets
        override fun save(tickets: List<EscalationTicket>) {
            this.tickets = tickets.toList()
        }
    }
}

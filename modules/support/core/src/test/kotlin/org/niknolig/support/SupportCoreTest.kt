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
        assertEquals(AnswerCode.UNRESOLVED, SupportAssistant.answer("Wann sendet die Email-App?").code)
    }

    @Test
    fun unknownAndUnavailableAccountQuestionsRequestHumanSupport() {
        assertTrue(SupportAssistant.answer("Wie setze ich mein Passwort zurück?").escalationRequired)
        assertTrue(SupportAssistant.answer("Bitte prüft den seltenen Code FRED-417").escalationRequired)
        assertTrue(SupportAssistant.answer(" ").escalationRequired)
        assertTrue(SupportAssistant.answer("é".repeat(1_025)).escalationRequired)
    }

    @Test
    fun crossTopicQuestionsRequireHumanSupport() {
        val answer = SupportAssistant.answer("Wie viel kostet die Zahlung für mein Konto?")
        assertEquals(AnswerCode.UNRESOLVED, answer.code)
        assertTrue(answer.escalationRequired)
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
        val queue = SupportEscalationQueue(store, clock = { 42L })
        val first = queue.enqueue(
            SupportApp.NIKNOLIG,
            "request-1",
            "UNRESOLVED",
            "NO_MATCH",
            "Y3lwaGVydGV4dA==",
        )
        val duplicate = queue.enqueue(
            SupportApp.NIKNOLIG,
            "request-1",
            "UNRESOLVED",
            "NO_MATCH",
            "different-ciphertext",
        )
        val defense = queue.enqueue(
            SupportApp.NIKNOLIG_DEFENSE,
            "request-1",
            "UNRESOLVED",
            "NO_MATCH",
            "Y3lwaGVydGV4dA==",
        )

        assertEquals(first, duplicate)
        assertEquals(42L, first.createdAtMillis)
        assertTrue(runCatching { java.util.UUID.fromString(first.id) }.isSuccess)
        assertEquals(2, queue.pending().size)
        assertFalse(store.load().joinToString().contains("customer text"))
        assertEquals(SupportApp.NIKNOLIG_DEFENSE, defense.app)
    }

    @Test
    fun failedHandoffIsRetainedAndRetriesAreBounded() {
        val store = MemoryTicketStore()
        val queue = SupportEscalationQueue(
            store,
            idGenerator = { "7ca68fc2-2e4c-4eef-8c56-89c478f554bb" },
            maxHandoffAttempts = 2,
        )
        val ticket = queue.enqueue(
            SupportApp.NIKNOLIG,
            "request-2",
            "BACKEND",
            "NETWORK_ERROR",
            "Y3lwaGVydGV4dA==",
        )

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
        val queue = SupportEscalationQueue(
            MemoryTicketStore(),
            idGenerator = { "7ca68fc2-2e4c-4eef-8c56-89c478f554bb" },
        )
        val ticket = queue.enqueue(
            SupportApp.NIKNOLIG_DEFENSE,
            "request-3",
            "UNRESOLVED",
            "NO_MATCH",
            "Y3lwaGVydGV4dA==",
        )

        queue.beginHandoff(ticket.id)
        assertEquals(HandoffState.HANDED_OFF, queue.finishHandoff(ticket.id, launched = true)?.handoffState)
        assertNull(queue.beginHandoff(ticket.id))
        assertTrue(queue.complete(ticket.id))
        assertTrue(queue.pending().isEmpty())
    }

    @Test
    fun metadataSharingAllowsOnlyFixedCodesAndMatchingApp() {
        val ticket = SupportEscalationQueue(MemoryTicketStore()).enqueue(
            SupportApp.NIKNOLIG, "request-4", "UNRESOLVED", "NO_MATCH", "Y3lwaGVydGV4dA==",
        )
        assertTrue(ticket.canShareMetadata(SupportApp.NIKNOLIG))
        assertFalse(ticket.canShareMetadata(SupportApp.NIKNOLIG_DEFENSE))
        assertFalse(ticket.copy(issueCode = "PRIVATE_CUSTOMER_TEXT").canShareMetadata(SupportApp.NIKNOLIG))
        assertFalse(ticket.copy(diagnosticCode = "PRIVATE_CUSTOMER_TEXT").canShareMetadata(SupportApp.NIKNOLIG))
        assertFalse(ticket.copy(id = "customer-text").canShareMetadata(SupportApp.NIKNOLIG))
        assertTrue(ticket.copy(encryptedPayload = "unreadable").canShareMetadata(SupportApp.NIKNOLIG))
    }

    @Test
    fun localDeletionWorksInEveryStateAndIsScopedAndPersistent() {
        HandoffState.entries.forEach { state ->
            val store = MemoryTicketStore()
            val queue = SupportEscalationQueue(store)
            val ticket = queue.enqueue(
                SupportApp.NIKNOLIG, "same-key", "UNRESOLVED", "NO_MATCH", "Y3lwaGVydGV4dA==",
            )
            val other = queue.enqueue(
                SupportApp.NIKNOLIG_DEFENSE, "same-key", "UNRESOLVED", "NO_MATCH", "Y3lwaGVydGV4dA==",
            )
            store.save(store.load().map {
                if (it.id == ticket.id) it.copy(handoffState = state, handoffAttempts = 3) else it
            })
            assertFalse(queue.remove(ticket.id, SupportApp.NIKNOLIG_DEFENSE))
            assertTrue(queue.remove(ticket.id, SupportApp.NIKNOLIG))
            assertFalse(queue.remove(ticket.id, SupportApp.NIKNOLIG))
            assertEquals(listOf(other), SupportEscalationQueue(store).pending())
            assertNull(queue.finishHandoff(ticket.id, launched = true))
            assertNull(queue.beginHandoff(ticket.id))
        }
    }

    @Test
    fun failedLocalDeletionDoesNotReportSuccessOrDropTicket() {
        val store = MemoryTicketStore()
        val queue = SupportEscalationQueue(store)
        val ticket = queue.enqueue(
            SupportApp.NIKNOLIG, "delete-failure", "UNRESOLVED", "NO_MATCH", "Y3lwaGVydGV4dA==",
        )
        store.failSave = true
        assertTrue(runCatching { queue.remove(ticket.id, SupportApp.NIKNOLIG) }.isFailure)
        assertEquals(listOf(ticket), queue.pending())
    }

    private class MemoryTicketStore : SupportTicketStore {
        private var tickets = emptyList<EscalationTicket>()
        var failSave = false
        override fun load() = tickets
        override fun save(tickets: List<EscalationTicket>) {
            check(!failSave)
            this.tickets = tickets.toList()
        }
    }
}

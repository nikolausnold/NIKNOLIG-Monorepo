package com.niknolig.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

private class MemoryPersistence(var value: String? = null, var fail: Boolean = false) : TextPersistence {
    override fun read() = value
    override fun write(value: String): Boolean {
        if (fail) return false
        this.value = value
        return true
    }
}

class LocalTaskRepositoryTest {
    private var counter = 0
    private fun repo(store: TextPersistence) = LocalTaskRepository(store) { "id${counter++}" }

    @Test
    fun addsEditsCompletesReopensAndDeletes() {
        val store = MemoryPersistence()
        val repo = repo(store)
        repo.add("  Akku prüfen  ")
        assertEquals(listOf(LocalTask("id0", "Akku prüfen", false)), repo.list())

        repo.rename("id0", "Akku laden")
        repo.setDone("id0", true)
        assertEquals(LocalTask("id0", "Akku laden", true), repo.list().single())

        repo.setDone("id0", false)
        assertFalse(repo.list().single().done)

        repo.delete("id0")
        assertTrue(repo.list().isEmpty())
    }

    @Test
    fun persistsAcrossRepositoryInstancesLikeARestart() {
        val store = MemoryPersistence()
        repo(store).add("Zeile | mit Sonderzeichen äöü & %")
        val reloaded = LocalTaskRepository(store).list()
        assertEquals("Zeile | mit Sonderzeichen äöü & %", reloaded.single().title)
    }

    @Test
    fun rejectsInvalidTitles() {
        val repo = repo(MemoryPersistence())
        assertEquals(TaskResult.Failure(TaskError.EMPTY), repo.add("   "))
        assertEquals(TaskResult.Failure(TaskError.TOO_LONG), repo.add("x".repeat(121)))
        assertEquals(TaskResult.Failure(TaskError.INVALID_CHARACTERS), repo.add("a\nb"))
        repo.add("ok")
        assertEquals(TaskResult.Failure(TaskError.EMPTY), repo.rename("id0", ""))
        assertEquals("ok", repo.list().single().title)
    }

    @Test
    fun enforcesLimitAndReportsUnknownIds() {
        val repo = repo(MemoryPersistence())
        repeat(LocalTaskRepository.MAX_TASKS) { repo.add("Aufgabe $it") }
        assertEquals(TaskResult.Failure(TaskError.LIMIT_REACHED), repo.add("zu viel"))
        assertEquals(TaskResult.Failure(TaskError.NOT_FOUND), repo.delete("missing"))
        assertEquals(TaskResult.Failure(TaskError.NOT_FOUND), repo.setDone("missing", true))
    }

    @Test
    fun reportsStorageFailureWithoutChangingStoredData() {
        val store = MemoryPersistence()
        val repo = repo(store)
        repo.add("bleibt")
        store.fail = true
        assertEquals(TaskResult.Failure(TaskError.STORAGE_FAILED), repo.add("neu"))
        assertEquals(listOf("bleibt"), repo.list().map { it.title })
    }

    @Test
    fun restoresVisibleValueWhenACommitFailsAfterChangingMemory() {
        var stored: String? = null
        var failNextWrite = false
        val persistence = RestoringTextPersistence(
            readValue = { stored },
            writeValue = { value ->
                stored = value
                if (failNextWrite) {
                    failNextWrite = false
                    false
                } else true
            },
        )
        val repo = repo(persistence)
        repo.add("bleibt")
        failNextWrite = true

        assertEquals(TaskResult.Failure(TaskError.STORAGE_FAILED), repo.add("nicht gespeichert"))
        assertEquals(listOf("bleibt"), repo.list().map { it.title })
    }

    @Test
    fun ignoresCorruptStoredLines() {
        val store = MemoryPersistence("garbage\nid1|1|Hallo\nid2|x|bad\nid3|0|%ZZ")
        assertEquals(listOf(LocalTask("id1", "Hallo", true)), LocalTaskRepository(store).list())
    }
}

class ConnectionLogTest {
    @Test
    fun tracksLastSuccessAndBoundedFailuresWithoutNotConfigured() {
        val log = ConnectionLog(MemoryPersistence())
        assertNull(log.state().lastSuccessMillis)

        log.record(ConnectionCode.NOT_CONFIGURED, 1)
        assertTrue(log.state().failures.isEmpty())

        log.record(ConnectionCode.TIMED_OUT, 2)
        log.record(ConnectionCode.READY, 3)
        log.record(ConnectionCode.NETWORK_ERROR, 4)
        val state = log.state()
        assertEquals(3L, state.lastSuccessMillis)
        assertEquals(listOf(ConnectionCode.TIMED_OUT, ConnectionCode.NETWORK_ERROR), state.failures.map { it.code })

        repeat(30) { log.record(ConnectionCode.HTTP_ERROR, 10L + it) }
        assertEquals(ConnectionLog.MAX_FAILURES, log.state().failures.size)
        assertEquals(3L, log.state().lastSuccessMillis)

        log.clear()
        assertNull(log.state().lastSuccessMillis)
        assertTrue(log.state().failures.isEmpty())
    }
}

class PairingGateTest {
    @Test
    fun isBlockedByDefaultWithAllOpenApprovals() {
        val gate = PairingGate.evaluate() as PairingGate.Blocked
        assertEquals(PairingBlocker.values().toList(), gate.blockers)
    }

    @Test
    fun staysBlockedUntilEveryApprovalExists() {
        val partial = PairingBlocker.values().toSet() - PairingBlocker.TWO_DEVICE_ACCEPTANCE_MISSING
        assertEquals(
            PairingGate.Blocked(listOf(PairingBlocker.TWO_DEVICE_ACCEPTANCE_MISSING)),
            PairingGate.evaluate(partial),
        )
        assertEquals(PairingGate.Open, PairingGate.evaluate(PairingBlocker.values().toSet()))
    }

    @Test
    fun overviewSeparatesEventsChecksAndBlockers() {
        val state = ConnectionState(
            5L,
            listOf(ConnectionFailure(1, ConnectionCode.TIMED_OUT), ConnectionFailure(2, ConnectionCode.HTTP_ERROR)),
        )
        val overview = SecurityOverview.build(
            listOf(
                SecurityCheck(SecurityCheckId.BACKUP_DISABLED, true),
                SecurityCheck(SecurityCheckId.NOT_DEBUGGABLE, false),
            ),
            state,
            PairingGate.evaluate(),
        )
        assertEquals(listOf(2L, 1L), overview.events.map { it.timeMillis })
        assertEquals(listOf(SecurityCheckId.NOT_DEBUGGABLE), overview.failedChecks)
        assertEquals(listOf(SecurityCheckId.BACKUP_DISABLED), overview.passedChecks)
        assertEquals(PairingBlocker.values().toList(), overview.blockers)
    }
}

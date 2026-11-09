package com.niknolig.defense

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class SecurityEventStoreTest {
    @Test
    fun recordsAnEmptyFindingsScanWithTheEmptyMarker() {
        val persistence = MemoryPersistence()

        val recorded = persistence.store.recordScan(emptyList())

        assertEquals(1, recorded.size)
        assertNull(recorded.single().finding)
        assertEquals(recorded, persistence.store.events())
        assertTrue(persistence.value!!.contains("\"finding\":\"\""))
    }

    @Test
    fun trimsTheEventLogToTheMostRecentHundredEvents() {
        val persistence = MemoryPersistence()

        repeat(105) {
            persistence.store.recordScan(listOf(SecurityFinding.DEBUGGABLE_BUILD))
        }

        assertEquals(100, persistence.store.events().size)
    }

    @Test
    fun skipsUnknownFindingCodesWithoutDiscardingKnownOrEmptyEvents() {
        val persistence = MemoryPersistence(
            """[
                {"timestamp":1,"finding":"UNKNOWN_FUTURE_FINDING"},
                {"timestamp":2,"finding":"DEBUGGABLE_BUILD"},
                {"timestamp":3,"finding":""},
                {"timestamp":4,"finding":"NO_SECURE_SCREEN_LOCK"}
            ]""",
        )

        val events = persistence.store.events()

        assertEquals(listOf(2L, 3L, 4L), events.map(SecurityEvent::timestamp))
        assertEquals(
            listOf(
                SecurityFinding.DEBUGGABLE_BUILD,
                null,
                SecurityFinding.NO_SECURE_SCREEN_LOCK,
            ),
            events.map(SecurityEvent::finding),
        )
    }

    @Test
    fun skipsMalformedEntriesAndKeepsTheRestOfTheLog() {
        val persistence = MemoryPersistence(
            """[
                {"timestamp":"invalid","finding":"DEBUGGABLE_BUILD"},
                {"timestamp":1,"finding":42},
                null,
                {"timestamp":2,"finding":"DEBUGGABLE_BUILD"}
            ]""",
        )

        assertEquals(
            listOf(SecurityEvent(2L, SecurityFinding.DEBUGGABLE_BUILD)),
            persistence.store.events(),
        )
    }

    @Test
    fun resetsMalformedStoredJsonSoFutureReadsCanRecover() {
        val persistence = MemoryPersistence("not-json")

        assertTrue(persistence.store.events().isEmpty())
        assertEquals("[]", persistence.value)
        assertTrue(persistence.store.events().isEmpty())
    }

    @Test
    fun resetsStoredEventsWhenReadingFailsSoFutureReadsCanRecover() {
        var value: String? = "previous"
        var failRead = true
        val store = SecurityEventStore(
            { if (failRead) error("read failed") else value },
            { value = it },
        )

        assertTrue(store.events().isEmpty())
        assertEquals("[]", value)
        failRead = false
        assertTrue(store.events().isEmpty())
    }

    private class MemoryPersistence(var value: String? = null) {
        val store = SecurityEventStore({ value }, { value = it })
    }
}

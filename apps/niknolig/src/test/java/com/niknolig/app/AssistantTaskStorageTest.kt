package com.niknolig.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class AssistantTaskStorageTest {
    @Test
    fun roundTripsTaskTitlesAndCompletionState() {
        val tasks = listOf(
            AssistantTask("first", "Review the draft", completed = true),
            AssistantTask("second", "Prüfe ✓ Eingabe\tmit Trennzeichen"),
        )

        assertEquals(tasks, AssistantTaskStorage.decode(AssistantTaskStorage.encode(tasks)))
    }

    @Test
    fun ignoresMalformedRecordsAndLimitsDecodedTasks() {
        val valid = AssistantTaskStorage.encode(
            (1..AssistantTaskStorage.MAX_TASKS + 1).map {
                AssistantTask("task-$it", "Task $it")
            },
        )

        assertEquals(
            AssistantTaskStorage.MAX_TASKS,
            AssistantTaskStorage.decode("$valid\ninvalid\t2\t@@@").size,
        )
    }

    @Test
    fun acceptsOnlyNonemptyBoundedTitlesWithoutControlCharacters() {
        assertEquals("Keep this", AssistantTaskStorage.validTitle("  Keep this  "))
        assertNull(AssistantTaskStorage.validTitle(" \n "))
        assertNull(AssistantTaskStorage.validTitle("x".repeat(AssistantTaskStorage.MAX_TITLE_CHARS + 1)))
        assertNull(AssistantTaskStorage.validTitle("unsafe\u0000title"))
    }
}

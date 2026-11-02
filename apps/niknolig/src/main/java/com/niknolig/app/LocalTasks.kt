package com.niknolig.app

import java.net.URLDecoder
import java.net.URLEncoder
import java.util.UUID

internal data class LocalTask(val id: String, val title: String, val done: Boolean)

internal enum class TaskError { EMPTY, TOO_LONG, INVALID_CHARACTERS, LIMIT_REACHED, NOT_FOUND, STORAGE_FAILED }

internal sealed class TaskResult {
    data class Success(val tasks: List<LocalTask>) : TaskResult()
    data class Failure(val error: TaskError) : TaskResult()
}

/** Minimal persistence port so the task logic can be tested without Android. */
internal interface TextPersistence {
    fun read(): String?
    fun write(value: String): Boolean
}

internal class RestoringTextPersistence(
    private val readValue: () -> String?,
    private val writeValue: (String) -> Boolean,
    private val restoreValue: (String?) -> Unit = { writeValue(it.orEmpty()) },
    private val lock: Any = Any(),
) : TextPersistence {
    override fun read(): String? = synchronized(lock) { readValue() }

    override fun write(value: String): Boolean = synchronized(lock) {
        val previous = readValue()
        if (writeValue(value)) true
        else {
            restoreValue(previous)
            false
        }
    }
}

/**
 * Local-only task list. Tasks live on this device and are not synchronized with
 * any other app, device or backend.
 */
internal class LocalTaskRepository(
    private val persistence: TextPersistence,
    private val newId: () -> String = { UUID.randomUUID().toString() },
) {
    fun list(): List<LocalTask> = decode(persistence.read())

    fun add(rawTitle: String): TaskResult {
        val title = validate(rawTitle) ?: return TaskResult.Failure(titleError(rawTitle))
        val current = list()
        if (current.size >= MAX_TASKS) return TaskResult.Failure(TaskError.LIMIT_REACHED)
        return save(current + LocalTask(newId(), title, done = false))
    }

    fun rename(id: String, rawTitle: String): TaskResult {
        val title = validate(rawTitle) ?: return TaskResult.Failure(titleError(rawTitle))
        return update(id) { it.copy(title = title) }
    }

    fun setDone(id: String, done: Boolean): TaskResult = update(id) { it.copy(done = done) }

    fun delete(id: String): TaskResult {
        val current = list()
        if (current.none { it.id == id }) return TaskResult.Failure(TaskError.NOT_FOUND)
        return save(current.filterNot { it.id == id })
    }

    private fun update(id: String, change: (LocalTask) -> LocalTask): TaskResult {
        val current = list()
        if (current.none { it.id == id }) return TaskResult.Failure(TaskError.NOT_FOUND)
        return save(current.map { if (it.id == id) change(it) else it })
    }

    private fun save(tasks: List<LocalTask>): TaskResult =
        if (persistence.write(encode(tasks))) TaskResult.Success(tasks)
        else TaskResult.Failure(TaskError.STORAGE_FAILED)

    companion object {
        const val MAX_TASKS = 50
        const val MAX_TITLE_LENGTH = 120

        fun validate(raw: String): String? {
            val title = raw.trim()
            return if (title.isNotEmpty() && title.length <= MAX_TITLE_LENGTH &&
                title.none { it.isISOControl() }
            ) title else null
        }

        private fun titleError(raw: String): TaskError {
            val title = raw.trim()
            return when {
                title.isEmpty() -> TaskError.EMPTY
                title.length > MAX_TITLE_LENGTH -> TaskError.TOO_LONG
                else -> TaskError.INVALID_CHARACTERS
            }
        }

        // One task per line: id|0-or-1|url-encoded title. Unreadable lines are skipped.
        internal fun encode(tasks: List<LocalTask>): String = tasks.joinToString("\n") {
            "${it.id}|${if (it.done) 1 else 0}|${URLEncoder.encode(it.title, "UTF-8")}"
        }

        internal fun decode(value: String?): List<LocalTask> =
            value.orEmpty().lineSequence().mapNotNull { line ->
                val parts = line.split('|')
                if (parts.size != 3 || parts[0].isEmpty() || parts[1] !in setOf("0", "1")) return@mapNotNull null
                val title = runCatching { URLDecoder.decode(parts[2], "UTF-8") }.getOrNull()
                    ?.let { validate(it) } ?: return@mapNotNull null
                LocalTask(parts[0], title, parts[1] == "1")
            }.take(MAX_TASKS).toList()
    }
}

package com.niknolig.app

import java.nio.charset.StandardCharsets
import java.util.Base64

internal data class AssistantTask(
    val id: String,
    val title: String,
    val completed: Boolean = false,
)

internal object AssistantTaskStorage {
    const val MAX_TASKS = 50
    const val MAX_TITLE_CHARS = 120

    fun validTitle(value: String): String? {
        val title = value.trim()
        if (title.isEmpty() || title.length > MAX_TITLE_CHARS || title.any(Char::isISOControl)) {
            return null
        }
        return title
    }

    fun encode(tasks: List<AssistantTask>): String =
        tasks.take(MAX_TASKS).joinToString("\n") { task ->
            val title = Base64.getUrlEncoder().withoutPadding()
                .encodeToString(task.title.toByteArray(StandardCharsets.UTF_8))
            "${task.id}\t${if (task.completed) 1 else 0}\t$title"
        }

    fun decode(value: String): List<AssistantTask> =
        value.lineSequence().mapNotNull { line ->
            val fields = line.split('\t', limit = 3)
            if (fields.size != 3 || fields[0].isBlank() || fields[0].any(Char::isISOControl)) {
                return@mapNotNull null
            }
            val completed = when (fields[1]) {
                "0" -> false
                "1" -> true
                else -> return@mapNotNull null
            }
            val decodedTitle = runCatching {
                String(Base64.getUrlDecoder().decode(fields[2]), StandardCharsets.UTF_8)
            }.getOrNull() ?: return@mapNotNull null
            val title = validTitle(decodedTitle) ?: return@mapNotNull null
            AssistantTask(fields[0], title, completed)
        }.take(MAX_TASKS).toList()
}

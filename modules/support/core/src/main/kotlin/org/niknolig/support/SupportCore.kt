package org.niknolig.support

enum class AnswerCode {
    BACKEND_HEALTH,
    PRIVACY,
    PAYMENT,
    TROUBLESHOOTING,
    ACCOUNT_UNAVAILABLE,
    UNRESOLVED,
}

data class SupportAnswer(
    val code: AnswerCode,
    val escalationRequired: Boolean,
)

enum class BackendDiagnostic(val escalationRequired: Boolean) {
    READY(false),
    NOT_CONFIGURED(true),
    INVALID_RESPONSE(true),
    TIMED_OUT(true),
    NETWORK_ERROR(true),
    HTTP_ERROR(true),
}

object SupportAssistant {
    const val MAX_QUESTION_BYTES = 2_048

    fun answer(question: String): SupportAnswer {
        if (question.isBlank() || question.toByteArray(Charsets.UTF_8).size > MAX_QUESTION_BYTES) {
            return SupportAnswer(AnswerCode.UNRESOLVED, true)
        }
        val normalized = question.lowercase()
        val words = Regex("[\\p{L}\\p{N}]+")
            .findAll(normalized)
            .map { it.value }
            .toSet()
        val matches = buildList {
            if (hasAny(words, "passwort", "password", "login", "konto", "account")) {
                add(AnswerCode.ACCOUNT_UNAVAILABLE)
            }
            if (hasAny(words, "zahlung", "preis", "payment", "rechnung", "billing")) {
                add(AnswerCode.PAYMENT)
            }
            if (hasAny(words, "datenschutz", "privacy", "daten", "data")) {
                add(AnswerCode.PRIVACY)
            }
            if (hasAny(words, "backend", "verbindung", "connection", "server", "ki", "ai")) {
                add(AnswerCode.BACKEND_HEALTH)
            }
            if (hasAny(words, "fehler", "problem", "funktioniert", "crash", "störung", "issue", "error")) {
                add(AnswerCode.TROUBLESHOOTING)
            }
        }
        if (matches.size != 1) return SupportAnswer(AnswerCode.UNRESOLVED, true)
        return SupportAnswer(
            matches.single(),
            matches.single() == AnswerCode.ACCOUNT_UNAVAILABLE,
        )
    }

    fun diagnose(diagnostic: BackendDiagnostic): BackendDiagnostic = diagnostic

    private fun hasAny(words: Set<String>, vararg terms: String): Boolean =
        terms.any { it in words }
}

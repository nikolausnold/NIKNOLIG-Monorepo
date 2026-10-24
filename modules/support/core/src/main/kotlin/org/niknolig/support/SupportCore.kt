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
    LIVE(false),
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
        return when {
            hasAny(words, "passwort", "password", "login", "konto", "account") ->
                SupportAnswer(AnswerCode.ACCOUNT_UNAVAILABLE, true)
            hasAny(words, "zahlung", "preis", "payment", "rechnung", "billing") ->
                SupportAnswer(AnswerCode.PAYMENT, false)
            hasAny(words, "datenschutz", "privacy", "daten", "data") ->
                SupportAnswer(AnswerCode.PRIVACY, false)
            hasAny(words, "backend", "verbindung", "connection", "server", "ki", "ai") ->
                SupportAnswer(AnswerCode.BACKEND_HEALTH, false)
            hasAny(words, "fehler", "problem", "funktioniert", "crash", "störung", "issue", "error") ->
                SupportAnswer(AnswerCode.TROUBLESHOOTING, false)
            else -> SupportAnswer(AnswerCode.UNRESOLVED, true)
        }
    }

    fun diagnose(diagnostic: BackendDiagnostic): BackendDiagnostic = diagnostic

    private fun hasAny(words: Set<String>, vararg terms: String): Boolean =
        terms.any { it in words }
}

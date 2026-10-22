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
        return when {
            listOf("passwort", "password", "login", "konto", "account").any(normalized::contains) ->
                SupportAnswer(AnswerCode.ACCOUNT_UNAVAILABLE, true)
            listOf("zahlung", "zahlung", "payment", "rechnung", "billing").any(normalized::contains) ->
                SupportAnswer(AnswerCode.PAYMENT, false)
            listOf("datenschutz", "privacy", "daten", "data").any(normalized::contains) ->
                SupportAnswer(AnswerCode.PRIVACY, false)
            listOf("backend", "verbindung", "connection", "server", "ki", "ai").any(normalized::contains) ->
                SupportAnswer(AnswerCode.BACKEND_HEALTH, false)
            listOf("fehler", "problem", "funktioniert", "crash", "störung", "issue", "error").any(normalized::contains) ->
                SupportAnswer(AnswerCode.TROUBLESHOOTING, false)
            else -> SupportAnswer(AnswerCode.UNRESOLVED, true)
        }
    }

    fun diagnose(diagnostic: BackendDiagnostic): BackendDiagnostic = diagnostic
}

package org.elektroengel.core

import java.net.SocketTimeoutException
import java.nio.charset.StandardCharsets
import java.util.Locale
import java.util.concurrent.TimeoutException

enum class AnalysisMode {
    WORD_BREAKDOWN,
    CONVENTION_SCAN,
    PERSPECTIVE_SHIFT,
    FACT_CHECK,
}

enum class SourceStatus {
    NOT_CHECKED,
}

enum class AnalysisFailure {
    EMPTY_INPUT,
    INVALID_INPUT,
    AI_DISABLED,
    PROVIDER_UNAVAILABLE,
    TIMEOUT,
}

data class AnalysisRequest(
    val mode: AnalysisMode,
    val text: String,
    val refinement: String = "",
)

data class AnalysisSection(
    val heading: String,
    val content: String,
)

data class AnalysisResult(
    val mode: AnalysisMode,
    val sections: List<AnalysisSection>,
    val uncertainty: String,
    val sourceStatus: SourceStatus = SourceStatus.NOT_CHECKED,
    val sources: List<String> = emptyList(),
)

sealed interface AnalysisOutcome {
    data class Success(val result: AnalysisResult) : AnalysisOutcome
    data class Failure(val reason: AnalysisFailure) : AnalysisOutcome
}

interface RemoteAnalysisAdapter {
    fun analyze(request: AnalysisRequest): AnalysisResult
}

object RemoteAnalysisStatus {
    fun unavailable(): AnalysisOutcome.Failure =
        AnalysisOutcome.Failure(AnalysisFailure.AI_DISABLED)

    fun failed(error: Throwable): AnalysisOutcome.Failure =
        AnalysisOutcome.Failure(AnalysisFailureMapper.from(error))
}

object AnalysisFailureMapper {
    fun from(error: Throwable): AnalysisFailure {
        var current: Throwable? = error
        repeat(16) {
            val cause = current ?: return AnalysisFailure.PROVIDER_UNAVAILABLE
            if (cause is TimeoutException || cause is SocketTimeoutException) {
                return AnalysisFailure.TIMEOUT
            }
            current = cause.cause
        }
        return AnalysisFailure.PROVIDER_UNAVAILABLE
    }
}

object ElectroEngelAnalyzer {
    private const val MAX_INPUT_CHARS = 1000
    private const val MAX_INPUT_BYTES = 2048
    private const val MAX_REFINEMENT_CHARS = 500

    private val wordGlosses = mapOf(
        "mutter" to "Kann eine Elternrolle, eine Anrede oder – je nach Zusammenhang – einen Fachbegriff bezeichnen.",
        "geld" to "Ein Arbeitsbegriff für allgemein verwendete Tausch- und Wertaufbewahrungsmittel; genaue Definitionen unterscheiden sich.",
        "treue" to "Kann Verlässlichkeit oder Beständigkeit in einer Beziehung, Bindung oder Aufgabe meinen.",
        "erfolg" to "Kann das Erreichen eines Ziels oder eines bewerteten Ergebnisses meinen; wer den Maßstab setzt, ist entscheidend.",
        "freiheit" to "Kann Handlungsspielraum oder Selbstbestimmung meinen; Rechte, Pflichten und tatsächliche Möglichkeiten setzen unterschiedliche Grenzen.",
    )

    fun analyze(request: AnalysisRequest): AnalysisOutcome {
        if (!isValid(request.text, request.refinement)) {
            return AnalysisOutcome.Failure(AnalysisFailure.INVALID_INPUT)
        }
        val text = request.text.trim()
        if (text.isEmpty()) return AnalysisOutcome.Failure(AnalysisFailure.EMPTY_INPUT)

        val subject = if (request.refinement.isBlank()) {
            text
        } else {
            "$text\n\nVertiefungsfrage: ${request.refinement.trim()}"
        }
        val sections = when (request.mode) {
            AnalysisMode.WORD_BREAKDOWN -> wordBreakdown(text, request.refinement)
            AnalysisMode.CONVENTION_SCAN -> conventionScan(subject)
            AnalysisMode.PERSPECTIVE_SHIFT -> perspectiveShift(subject)
            AnalysisMode.FACT_CHECK -> factCheck(subject)
        }
        return AnalysisOutcome.Success(
            AnalysisResult(
                mode = request.mode,
                sections = sections,
                uncertainty = "Sprachliche, regelbasierte Erstprüfung. Keine Wörterbuch-, Quellen- oder Faktenrecherche; Aussagen und Einordnungen können unvollständig sein.",
            ),
        )
    }

    private fun isValid(text: String, refinement: String): Boolean {
        val bytes = text.toByteArray(StandardCharsets.UTF_8).size
        val controls = text.any { it.isISOControl() && it != '\n' && it != '\r' && it != '\t' }
        val refinementControls =
            refinement.any { it.isISOControl() && it != '\n' && it != '\r' && it != '\t' }
        return text.length <= MAX_INPUT_CHARS &&
            bytes <= MAX_INPUT_BYTES &&
            refinement.length <= MAX_REFINEMENT_CHARS &&
            !controls &&
            !refinementControls
    }

    private fun wordBreakdown(text: String, refinement: String): List<AnalysisSection> {
        val key = text.trim().lowercase(Locale.ROOT).trimEnd('.', '!', '?')
        val gloss = wordGlosses[key]
            ?: "Für diesen Begriff liegt keine kuratierte Arbeitsfassung vor. Bedeutung und Gebrauch hängen vom Satz und Kontext ab."
        return listOf(
            AnalysisSection("Wortbedeutung · Arbeitsfassung", gloss),
            AnalysisSection(
                "Wortgeschichte",
                "Nicht geprüft. Ohne ein verlässliches etymologisches Wörterbuch oder einen historischen Beleg wird keine Herkunft behauptet.",
            ),
            AnalysisSection(
                "Kulturelle Prägung",
                "Gebrauch und Wertung können sich zwischen Gemeinschaften, Zeiten und Lebensbereichen unterscheiden. Eine konkrete Zuordnung wurde nicht recherchiert.",
            ),
            AnalysisSection(
                "Persönliche Interpretation",
                refinement.takeIf { it.isNotBlank() }
                    ?: "Welche Erfahrung, Erwartung oder Wertung verbindest du persönlich mit „$text“?",
            ),
        )
    }

    private fun conventionScan(text: String): List<AnalysisSection> {
        val normalized = text.lowercase(Locale.ROOT)
        val matches = mutableListOf<String>()
        if (containsAny(normalized, "messbar", "misst", "beträgt", "gezählt", "beobachtet", "nachweisbar", "experiment")) {
            matches += "Empirisch überprüfbar: Der Wortlaut verweist auf Beobachtung, Messung oder einen möglichen Nachweis; konkrete Daten wurden nicht geprüft."
        }
        if (containsAny(normalized, "bedeutet", "definition", "definiert als", "unter ... versteht")) {
            matches += "Definitorisch: Die Aussage scheint einen Begriff festzulegen oder zu erläutern; damit ist die Definition nicht automatisch allgemein anerkannt."
        }
        if (containsAny(normalized, "üblich", "tradition", "normal", "gesellschaftlich", "gesetzlich", "vereinbart", "konvention")) {
            matches += "Gesellschaftlich vereinbart: Die Formulierung deutet auf eine Regel, Erwartung oder Praxis hin; Reichweite und tatsächliche Zustimmung bleiben offen."
        }
        if (containsAny(normalized, "sollte", "muss", "darf nicht", "richtig", "falsch", "gerecht", "verpflichtet")) {
            matches += "Normativ: Die Aussage enthält ein Sollen, Dürfen oder eine Bewertung; sie braucht eine benannte Begründung oder Wertgrundlage."
        }
        if (containsAny(normalized, "ich finde", "für mich", "meiner meinung", "ich glaube", "fühlt sich")) {
            matches += "Persönlich: Der Wortlaut markiert eine eigene Einschätzung oder Erfahrung; sie belegt keine allgemeine Tatsache."
        }
        if (matches.isEmpty()) {
            matches += "Noch nicht eindeutig einzuordnen: Im Wortlaut fehlen klare Hinweise auf Prüfbarkeit, Definition, Vereinbarung, Wertung oder persönliche Sicht."
        }
        return listOf(
            AnalysisSection("Mögliche Einordnungen", matches.joinToString("\n\n")),
            AnalysisSection(
                "Begründung und Grenze",
                "Die Zuordnung folgt nur erkennbaren Sprachhinweisen. Eine Aussage kann zugleich mehrere Kategorien enthalten; die Einordnung bestätigt weder ihre Wahrheit noch ihre Geltung.",
            ),
        )
    }

    private fun perspectiveShift(text: String): List<AnalysisSection> {
        val absolutism = containsAny(
            text.lowercase(Locale.ROOT),
            "immer", "niemals", "alle ", "jeder ", "niemand", "ausschließlich", "nur ",
        )
        val counterpoint = if (absolutism) {
            "Gegenfrage: Gibt es einen konkreten Gegenfall oder eine Gruppe, für die die Aussage nicht gilt?"
        } else {
            "Gegenfrage: Unter welchen Bedingungen würde eine vernünftige Person zu einer anderen Einschätzung kommen?"
        }
        return listOf(
            AnalysisSection(
                "Historische Perspektive",
                "Frage, wie sich Bedeutung, Bedingungen und Folgen über verschiedene Zeiten verändert haben könnten. Ohne konkrete Quellen wird keine historische Entwicklung behauptet.",
            ),
            AnalysisSection(
                "Kulturelle Perspektive",
                "Frage, welche unterschiedlichen Erfahrungen, Rollen oder örtlichen Gepflogenheiten die Sicht beeinflussen könnten. Es wird keiner konkreten Kultur eine Position zugeschrieben.",
            ),
            AnalysisSection(
                "Philosophische Perspektive",
                "Prüfe, welche Werte oder Begriffe vorausgesetzt werden und ob individuelle Freiheit, gemeinsame Pflichten und Folgen unterschiedlich gewichtet werden.",
            ),
            AnalysisSection(
                "Gemeinsamkeiten, Unterschiede und Gegenargument",
                "Gemeinsamkeit: Jede Perspektive kann nach Voraussetzungen und Folgen fragen. Unterschiede entstehen durch Maßstab und Gewichtung; alternative Sichtweisen sind keine bewiesenen Tatsachen.\n\n$counterpoint\n\nAusgangspunkt: „$text“",
            ),
        )
    }

    private fun factCheck(text: String): List<AnalysisSection> {
        val sentences = text.split(Regex("(?<=[.!?])\\s+")).filter(String::isNotBlank)
        val claims = sentences.map { sentence ->
            val lower = sentence.lowercase(Locale.ROOT)
            val labels = mutableListOf<String>()
            if (containsAny(lower, "ich glaube", "ich finde", "meiner meinung", "für mich")) {
                labels += "Meinung / persönliche Einschätzung"
            }
            if (containsAny(lower, "vielleicht", "möglicherweise", "vermutlich", "könnte", "wahrscheinlich")) {
                labels += "Hypothese / Vermutung"
            }
            if (containsAny(lower, "also", "daher", "deshalb", "folglich", "somit")) {
                labels += "Schlussfolgerung"
            }
            if (labels.isEmpty()) labels += "Möglicherweise überprüfbare Tatsachenbehauptung"
            "• ${labels.joinToString(" + ")}: $sentence"
        }
        val flags = mutableListOf<String>()
        if (containsAny(text.lowercase(Locale.ROOT), "immer", "niemals", "alle ", "jeder ", "niemand", "keiner ")) {
            flags += "Pauschalisierungssignal: absolute Wörter wie „alle“, „immer“ oder „niemand“ verlangen Gegenbeispiele und eine klar begrenzte Gruppe."
        }
        if (Regex("""\b(ist|sind|hat|haben)\b[^.!?]{0,100}\b(und|aber)\b[^.!?]{0,50}\b(nicht|kein|keine|keiner)\b""", RegexOption.IGNORE_CASE).containsMatchIn(text)) {
            flags += "Möglicher Widerspruch: der Satz verbindet eine Behauptung und eine Verneinung. Prüfe, ob wirklich derselbe Gegenstand, Zeitraum und Sinn gemeint ist."
        }
        if (flags.isEmpty()) {
            flags += "Keine dieser einfachen Muster wurde eindeutig erkannt. Das beweist weder Widerspruchsfreiheit noch Richtigkeit."
        }
        return listOf(
            AnalysisSection("Aussagenarten · vorläufig", claims.joinToString("\n")),
            AnalysisSection("Denkfehler-Signale", flags.joinToString("\n\n")),
            AnalysisSection(
                "Fakten- und Quellenstatus",
                "Keine externe Quelle wurde abgefragt. Hypothesen, Meinungen und Schlussfolgerungen sind nicht als bestätigte Fakten zu lesen.",
            ),
        )
    }

    private fun containsAny(text: String, vararg cues: String): Boolean =
        cues.any(text::contains)
}

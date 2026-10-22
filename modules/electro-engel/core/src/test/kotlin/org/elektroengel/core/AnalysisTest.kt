package org.elektroengel.core

import java.net.SocketTimeoutException
import java.util.concurrent.TimeoutException
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AnalysisTest {
    @Test
    fun wordBreakdownSeparatesMeaningHistoryCultureAndPersonalInterpretation() {
        val result = success(AnalysisMode.WORD_BREAKDOWN, "Freiheit")

        assertEquals(
            listOf(
                "Wortbedeutung · Arbeitsfassung",
                "Wortgeschichte",
                "Kulturelle Prägung",
                "Persönliche Interpretation",
            ),
            result.sections.map(AnalysisSection::heading),
        )
        assertTrue(result.sections[0].content.contains("Selbstbestimmung"))
        assertTrue(result.sections[1].content.contains("Nicht geprüft"))
        assertTrue(result.sections[3].content.contains("persönlich"))
    }

    @Test
    fun conventionScanAllowsMixedCategoriesAndExplainsHeuristicLimits() {
        val result = success(
            AnalysisMode.CONVENTION_SCAN,
            "Ich finde, Erfolg bedeutet, dass die Gesellschaft das Ergebnis misst und man sich an die Tradition halten sollte.",
        )
        val analysis = result.sections.joinToString("\n") { "${it.heading}\n${it.content}" }

        assertTrue(analysis.contains("Persönlich"))
        assertTrue(analysis.contains("Definitorisch"))
        assertTrue(analysis.contains("Empirisch überprüfbar"))
        assertTrue(analysis.contains("Gesellschaftlich vereinbart"))
        assertTrue(analysis.contains("Normativ"))
        assertTrue(analysis.contains("bestätigt weder ihre Wahrheit"))
    }

    @Test
    fun perspectiveShiftOffersDistinctLensesAndDoesNotAssertCulturalFacts() {
        val result = success(AnalysisMode.PERSPECTIVE_SHIFT, "Alle Menschen wollen immer Erfolg.")
        val analysis = result.sections.joinToString("\n") { "${it.heading}\n${it.content}" }

        assertEquals(4, result.sections.size)
        assertTrue(analysis.contains("Historische Perspektive"))
        assertTrue(analysis.contains("Kulturelle Perspektive"))
        assertTrue(analysis.contains("Philosophische Perspektive"))
        assertTrue(analysis.contains("Gegenfrage"))
        assertTrue(analysis.contains("keiner konkreten Kultur eine Position zugeschrieben"))
    }

    @Test
    fun factCheckLabelsStatementsAndFlagsAbsoluteClaimsAndPossibleContradiction() {
        val result = success(
            AnalysisMode.FACT_CHECK,
            "Alle Menschen sind immer glücklich und sind nicht glücklich. Ich finde, Erfolg könnte wichtig sein.",
        )
        val analysis = result.sections.joinToString("\n") { it.content }

        assertTrue(analysis.contains("Meinung / persönliche Einschätzung"))
        assertTrue(analysis.contains("Hypothese / Vermutung"))
        assertTrue(analysis.contains("Pauschalisierungssignal"))
        assertTrue(analysis.contains("Möglicher Widerspruch"))
        assertTrue(analysis.contains("Keine externe Quelle wurde abgefragt"))
    }

    @Test
    fun invalidInputsAreRejectedAndRefinementIsAppliedWithoutStorage() {
        assertEquals(
            AnalysisOutcome.Failure(AnalysisFailure.EMPTY_INPUT),
            ElectroEngelAnalyzer.analyze(AnalysisRequest(AnalysisMode.FACT_CHECK, " \n ")),
        )
        assertEquals(
            AnalysisOutcome.Failure(AnalysisFailure.INVALID_INPUT),
            ElectroEngelAnalyzer.analyze(AnalysisRequest(AnalysisMode.FACT_CHECK, "x".repeat(1001))),
        )
        assertEquals(
            AnalysisOutcome.Failure(AnalysisFailure.INVALID_INPUT),
            ElectroEngelAnalyzer.analyze(AnalysisRequest(AnalysisMode.FACT_CHECK, " ".repeat(1001))),
        )
        assertEquals(
            AnalysisOutcome.Failure(AnalysisFailure.INVALID_INPUT),
            ElectroEngelAnalyzer.analyze(AnalysisRequest(AnalysisMode.FACT_CHECK, "\u0800".repeat(1000))),
        )
        assertEquals(
            AnalysisOutcome.Failure(AnalysisFailure.INVALID_INPUT),
            ElectroEngelAnalyzer.analyze(AnalysisRequest(AnalysisMode.FACT_CHECK, "These", "\u0000")),
        )

        val refined = success(AnalysisMode.PERSPECTIVE_SHIFT, "Freiheit", "Wessen Freiheit?")
        assertTrue(refined.sections.last().content.contains("Wessen Freiheit?"))
        assertFalse(refined.sections.any { it.content.contains("vorherige Analyse") })
    }

    @Test
    fun sourcesRemainExplicitlyUncheckedAndNoSourceIsInvented() {
        val result = success(AnalysisMode.WORD_BREAKDOWN, "Begriff ohne Eintrag")

        assertEquals(SourceStatus.NOT_CHECKED, result.sourceStatus)
        assertTrue(result.sources.isEmpty())
        assertTrue(result.uncertainty.contains("Keine Wörterbuch-, Quellen- oder Faktenrecherche"))
        assertTrue(result.sections[1].content.contains("keine Herkunft behauptet"))
    }

    @Test
    fun unavailableAiAndTimeoutFailuresMapToSafeStates() {
        assertEquals(
            AnalysisFailure.TIMEOUT,
            AnalysisFailureMapper.from(IllegalStateException("provider", SocketTimeoutException())),
        )
        assertEquals(
            AnalysisFailure.TIMEOUT,
            AnalysisFailureMapper.from(TimeoutException()),
        )
        assertEquals(
            AnalysisFailure.PROVIDER_UNAVAILABLE,
            AnalysisFailureMapper.from(IllegalStateException("private input")),
        )
        val privateFailure = RemoteAnalysisStatus.failed(
            IllegalStateException("private input", SocketTimeoutException("secret prompt")),
        )
        assertFalse(privateFailure.toString().contains("secret prompt"))
        assertEquals(
            AnalysisOutcome.Failure(AnalysisFailure.AI_DISABLED),
            RemoteAnalysisStatus.unavailable(),
        )
        assertEquals(
            AnalysisOutcome.Failure(AnalysisFailure.TIMEOUT),
            RemoteAnalysisStatus.failed(TimeoutException()),
        )
    }

    private fun success(mode: AnalysisMode, text: String, refinement: String = ""): AnalysisResult =
        (ElectroEngelAnalyzer.analyze(AnalysisRequest(mode, text, refinement)) as AnalysisOutcome.Success).result
}

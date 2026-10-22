import Foundation
import XCTest
@testable import ElectroEngelCore

final class ElectroEngelAnalyzerTests: XCTestCase {
    func testWordBreakdownKeepsMeaningHistoryCultureAndPersonalInterpretationSeparate() throws {
        let result = try success(.wordBreakdown, "Freiheit")

        XCTAssertEqual(
            result.sections.map(\.heading),
            ["Wortbedeutung · Arbeitsfassung", "Wortgeschichte", "Kulturelle Prägung", "Persönliche Interpretation"]
        )
        XCTAssertTrue(result.sections[0].content.contains("Selbstbestimmung"))
        XCTAssertTrue(result.sections[1].content.contains("Nicht geprüft"))
        XCTAssertTrue(result.sections[3].content.contains("persönlich"))
    }

    func testConventionScannerReportsMixedSignalsAndExplainsLimits() throws {
        let result = try success(
            .conventionScan,
            "Ich finde, Erfolg bedeutet, dass die Gesellschaft das Ergebnis misst und man sich an die Tradition halten sollte."
        )
        let analysis = result.sections.map { "\($0.heading)\n\($0.content)" }.joined(separator: "\n")

        for category in ["Persönlich", "Definitorisch", "Empirisch überprüfbar", "Gesellschaftlich vereinbart", "Normativ"] {
            XCTAssertTrue(analysis.contains(category), "Missing category: \(category)")
        }
        XCTAssertTrue(analysis.contains("bestätigt weder ihre Wahrheit"))
    }

    func testPerspectiveShiftShowsDistinctLensesAndDoesNotAssertCulturalFacts() throws {
        let result = try success(.perspectiveShift, "Alle Menschen wollen immer Erfolg.")
        let analysis = result.sections.map { "\($0.heading)\n\($0.content)" }.joined(separator: "\n")

        XCTAssertEqual(result.sections.count, 4)
        XCTAssertTrue(analysis.contains("Historische Perspektive"))
        XCTAssertTrue(analysis.contains("Kulturelle Perspektive"))
        XCTAssertTrue(analysis.contains("Philosophische Perspektive"))
        XCTAssertTrue(analysis.contains("Gegenfrage"))
        XCTAssertTrue(analysis.contains("keiner konkreten Kultur eine Position zugeschrieben"))
    }

    func testFactCheckSeparatesStatementTypesAndFlagsGeneralizationAndContradiction() throws {
        let result = try success(
            .factCheck,
            "Alle Menschen sind immer glücklich und sind nicht glücklich. Ich finde, Erfolg könnte wichtig sein."
        )
        let analysis = result.sections.map { "\($0.heading)\n\($0.content)" }.joined(separator: "\n")

        for signal in ["Meinung / persönliche Einschätzung", "Hypothese / Vermutung", "Pauschalisierungssignal", "Möglicher Widerspruch", "Keine externe Quelle wurde abgefragt"] {
            XCTAssertTrue(analysis.contains(signal), "Missing signal: \(signal)")
        }
    }

    func testEmptyOversizedAndControlCharacterInputsFailClosed() {
        XCTAssertFailure(.emptyInput, ElectroEngelAnalyzer.analyze(request(.factCheck, " \n ")))
        XCTAssertFailure(.invalidInput, ElectroEngelAnalyzer.analyze(request(.factCheck, String(repeating: "x", count: 1_001))))
        XCTAssertFailure(.invalidInput, ElectroEngelAnalyzer.analyze(request(.factCheck, String(repeating: " ", count: 1_001))))
        XCTAssertFailure(.invalidInput, ElectroEngelAnalyzer.analyze(request(.factCheck, String(repeating: "\u{0800}", count: 1_000))))
        XCTAssertFailure(.invalidInput, ElectroEngelAnalyzer.analyze(request(.factCheck, "A\u{0000}B")))
        XCTAssertFailure(.invalidInput, ElectroEngelAnalyzer.analyze(ElectroEngelRequest(mode: .factCheck, text: "A", refinement: "\u{0000}")))
    }

    func testRefinementIsUsedWithoutClaimingExternalSources() throws {
        let result = try success(.perspectiveShift, "Freiheit", refinement: "Wessen Freiheit?")

        XCTAssertTrue(result.sections.last?.content.contains("Wessen Freiheit?") == true)
        XCTAssertEqual(result.sourceStatus, "Nicht geprüft; es wurde keine externe Quelle abgefragt.")
        XCTAssertTrue(result.sources.isEmpty)
    }

    func testUnknownWordDoesNotInventEtymologyOrCitations() throws {
        let result = try success(.wordBreakdown, "Ein unbekannter Fachbegriff")

        XCTAssertTrue(result.sections[0].content.contains("keine kuratierte Arbeitsfassung"))
        XCTAssertTrue(result.sections[1].content.contains("keine Herkunft behauptet"))
        XCTAssertTrue(result.sources.isEmpty)
    }

    func testAiBoundaryIsDisabledAndProviderFailuresAreGeneric() {
        XCTAssertFailure(.aiDisabled, ElectroEngelRemoteBoundary.unavailable())
        XCTAssertFailure(.timeout, ElectroEngelRemoteBoundary.failed(URLError(.timedOut)))
        XCTAssertFailure(.providerUnavailable, ElectroEngelRemoteBoundary.failed(URLError(.cannotConnectToHost)))
        let privateFailure = ElectroEngelRemoteBoundary.failed(NSError(domain: "private prompt", code: 1))
        XCTAssertFalse(String(describing: privateFailure).contains("private prompt"))
    }

    private func request(
        _ mode: ElectroEngelMode,
        _ text: String,
        refinement: String = ""
    ) -> ElectroEngelRequest {
        ElectroEngelRequest(mode: mode, text: text, refinement: refinement)
    }

    private func success(
        _ mode: ElectroEngelMode,
        _ text: String,
        refinement: String = ""
    ) throws -> ElectroEngelResult {
        guard case .success(let result) = ElectroEngelAnalyzer.analyze(request(mode, text, refinement: refinement)) else {
            throw NSError(domain: "ElectroEngelCoreTests", code: 1)
        }
        return result
    }

    private func XCTAssertFailure(
        _ expected: ElectroEngelFailure,
        _ outcome: ElectroEngelOutcome,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        guard case .failure(let failure) = outcome else {
            XCTFail("Expected failure \(expected)", file: file, line: line)
            return
        }
        XCTAssertEqual(failure, expected, file: file, line: line)
    }
}

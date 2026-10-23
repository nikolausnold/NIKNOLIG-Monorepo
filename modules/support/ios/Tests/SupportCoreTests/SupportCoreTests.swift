import XCTest
@testable import SupportCore

final class SupportCoreTests: XCTestCase {
    func testCommonQuestionsReceiveDeterministicAnswers() {
        XCTAssertEqual(SupportAssistant.answer("Wie prüfe ich die Verbindung?").code, .backendHealth)
        XCTAssertEqual(SupportAssistant.answer("Was passiert mit meinen Daten?").code, .privacy)
        XCTAssertEqual(SupportAssistant.answer("Frage zur Zahlung").code, .payment)
        XCTAssertEqual(SupportAssistant.answer("Die App funktioniert nicht").code, .troubleshooting)
        XCTAssertEqual(SupportAssistant.answer("Wann sendet die Email-App?").code, .unresolved)
    }

    func testUnknownQuestionsAndUnavailableAccountsRequireEscalation() {
        XCTAssertTrue(SupportAssistant.answer("Passwort wiederherstellen").escalationRequired)
        XCTAssertTrue(SupportAssistant.answer("Bitte prüft den seltenen Code FRED-417").escalationRequired)
        XCTAssertTrue(SupportAssistant.answer(" ").escalationRequired)
        XCTAssertTrue(SupportAssistant.answer(String(repeating: "é", count: 1_025)).escalationRequired)
    }

    func testCrossTopicQuestionsRequireHumanSupport() {
        let answer = SupportAssistant.answer("Wie viel kostet die Zahlung für mein Konto?")
        XCTAssertEqual(answer.code, .unresolved)
        XCTAssertTrue(answer.escalationRequired)
    }

    func testDiagnosticsEscalateOnlyWhenHealthCheckFails() {
        XCTAssertFalse(SupportDiagnostic.ready.escalationRequired)
        for diagnostic in [
            SupportDiagnostic.notConfigured, .invalidResponse, .timedOut,
            .networkError, .httpError
        ] {
            XCTAssertTrue(diagnostic.escalationRequired)
        }
    }

    func testQueueScopesAppsAndDeduplicatesTickets() throws {
        let store = MemoryTicketStore()
        let queue = SupportEscalationQueue(store: store, clock: { 42 })
        let first = try queue.enqueue(
            app: .niknolig,
            requestKey: "question-1",
            issueCode: "UNKNOWN",
            diagnosticCode: "NO_MATCH",
            encryptedPayload: "Y3lwaGVydGV4dA=="
        )
        let duplicate = try queue.enqueue(
            app: .niknolig,
            requestKey: "question-1",
            issueCode: "UNKNOWN",
            diagnosticCode: "NO_MATCH",
            encryptedPayload: "different-ciphertext"
        )
        let defense = try queue.enqueue(
            app: .niknoligDefense,
            requestKey: "question-1",
            issueCode: "UNKNOWN",
            diagnosticCode: "NO_MATCH",
            encryptedPayload: "Y3lwaGVydGV4dA=="
        )

        XCTAssertEqual(first, duplicate)
        XCTAssertEqual(first.createdAtMilliseconds, 42)
        XCTAssertFalse(try queue.tickets().description.contains("customer question"))
        XCTAssertEqual(try queue.tickets().count, 2)
        XCTAssertEqual(defense.app, .niknoligDefense)
    }

    func testFailedHandoffPersistsAndLimitsRetries() throws {
        let store = MemoryTicketStore()
        let queue = SupportEscalationQueue(store: store)
        let ticket = try queue.enqueue(
            app: .niknolig,
            requestKey: "backend-1",
            issueCode: "BACKEND",
            diagnosticCode: "NETWORK_ERROR",
            encryptedPayload: "Y3lwaGVydGV4dA=="
        )

        for attempt in 1...SupportEscalationQueue.maxHandoffAttempts {
            XCTAssertEqual(try queue.beginHandoff(ticket.id)?.handoffState, .uncertain)
            XCTAssertEqual(try queue.finishHandoff(ticket.id, launched: false)?.handoffState, .ready)
            XCTAssertEqual(try queue.tickets().first?.handoffAttempts, attempt)
        }
        XCTAssertNil(try queue.beginHandoff(ticket.id))
        XCTAssertEqual(try queue.tickets().count, 1)
    }

    func testSuccessfulHandoffCannotBeRepeatedAndCanBeCompleted() throws {
        let queue = SupportEscalationQueue(store: MemoryTicketStore())
        let ticket = try queue.enqueue(
            app: .niknoligDefense,
            requestKey: "question-2",
            issueCode: "UNKNOWN",
            diagnosticCode: "NO_MATCH",
            encryptedPayload: "Y3lwaGVydGV4dA=="
        )

        _ = try queue.beginHandoff(ticket.id)
        XCTAssertEqual(try queue.finishHandoff(ticket.id, launched: true)?.handoffState, .handedOff)
        XCTAssertNil(try queue.beginHandoff(ticket.id))
        XCTAssertTrue(try queue.complete(ticket.id))
        XCTAssertTrue(try queue.tickets().isEmpty)
    }

    func testMetadataSharingAllowsOnlyFixedCodesAndMatchingApp() {
        func ticket(issue: String = "UNRESOLVED", diagnostic: String = "NO_MATCH") -> EscalationTicket {
            EscalationTicket(
                app: .niknolig, requestKey: "metadata", issueCode: issue,
                diagnosticCode: diagnostic, encryptedPayload: "unreadable"
            )
        }
        XCTAssertTrue(ticket().canShareMetadata(for: .niknolig))
        XCTAssertFalse(ticket().canShareMetadata(for: .niknoligDefense))
        XCTAssertFalse(ticket(issue: "PRIVATE_CUSTOMER_TEXT").canShareMetadata(for: .niknolig))
        XCTAssertFalse(ticket(diagnostic: "PRIVATE_CUSTOMER_TEXT").canShareMetadata(for: .niknolig))
    }

    func testLocalDeletionWorksInEveryStateAndIsScopedAndPersistent() throws {
        for state in [HandoffState.ready, .uncertain, .handedOff] {
            let store = MemoryTicketStore()
            let queue = SupportEscalationQueue(store: store)
            let ticket = try queue.enqueue(
                app: .niknolig, requestKey: "same-key", issueCode: "UNRESOLVED",
                diagnosticCode: "NO_MATCH", encryptedPayload: "Y3lwaGVydGV4dA=="
            )
            let other = try queue.enqueue(
                app: .niknoligDefense, requestKey: "same-key", issueCode: "UNRESOLVED",
                diagnosticCode: "NO_MATCH", encryptedPayload: "Y3lwaGVydGV4dA=="
            )
            try store.save(store.load().map {
                var updated = $0
                if updated.id == ticket.id {
                    updated.handoffState = state
                    updated.handoffAttempts = SupportEscalationQueue.maxHandoffAttempts
                }
                return updated
            })
            XCTAssertFalse(try queue.remove(ticket.id, app: .niknoligDefense))
            XCTAssertTrue(try queue.remove(ticket.id, app: .niknolig))
            XCTAssertFalse(try queue.remove(ticket.id, app: .niknolig))
            XCTAssertEqual(try SupportEscalationQueue(store: store).tickets(), [other])
            XCTAssertNil(try queue.finishHandoff(ticket.id, launched: true))
            XCTAssertNil(try queue.beginHandoff(ticket.id))
        }
    }

    func testFailedLocalDeletionDoesNotReportSuccessOrDropTicket() throws {
        let store = MemoryTicketStore()
        let queue = SupportEscalationQueue(store: store)
        let ticket = try queue.enqueue(
            app: .niknolig, requestKey: "delete-failure", issueCode: "UNRESOLVED",
            diagnosticCode: "NO_MATCH", encryptedPayload: "Y3lwaGVydGV4dA=="
        )
        store.failSave = true
        XCTAssertThrowsError(try queue.remove(ticket.id, app: .niknolig))
        XCTAssertEqual(try queue.tickets(), [ticket])
    }

    private final class MemoryTicketStore: SupportTicketStore {
        private var stored: [EscalationTicket] = []
        var failSave = false
        func load() throws -> [EscalationTicket] { stored }
        func save(_ tickets: [EscalationTicket]) throws {
            if failSave { throw SupportQueueError.encryptionFailed }
            stored = tickets
        }
    }
}

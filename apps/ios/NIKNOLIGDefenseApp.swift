import Foundation
import SwiftUI

@main
struct NIKNOLIGDefenseApp: App {
    var body: some Scene {
        WindowGroup {
            DefenseHomeView()
        }
    }
}

private enum DefenseRoute: Hashable {
    case profile
    case support
}

private enum DefenseHealthState: Equatable {
    case notConfigured
    case checking
    case ready
    case unavailable
}

private struct DefenseHomeView: View {
    @State private var path: [DefenseRoute] = []

    var body: some View {
        NavigationStack(path: $path) {
            List {
                Section {
                    Text("Vorschau – diese App löst keinen Notruf aus und übermittelt keine Standort- oder Notfallinformationen.")
                        .foregroundStyle(.secondary)
                }
                Section("NIKNOLIG Defense") {
                    Text("Notfall- und Infrastruktur-Erkennungsfunktionen sind in dieser Version nicht verfügbar.")
                        .foregroundStyle(.secondary)
                    NavigationLink("Lernprofil", value: DefenseRoute.profile)
                    NavigationLink("Support", value: DefenseRoute.support)
                }
            }
            .navigationTitle("NIKNOLIG Defense")
            .navigationDestination(for: DefenseRoute.self) { route in
                switch route {
                case .profile: DefenseProfileView()
                case .support: DefenseSupportView()
                }
            }
        }
        .tint(Color(red: 0.66, green: 0.87, blue: 0.24))
    }
}

private struct DefenseProfileView: View {
    @AppStorage("learning_enabled") private var learningEnabled = false
    @AppStorage("response_style") private var responseStyle = "concise"
    @AppStorage("session_summary") private var sessionSummary = ""
    @AppStorage("helpful_count") private var helpfulCount = 0
    @AppStorage("unclear_count") private var unclearCount = 0
    @AppStorage("correction_count") private var correctionCount = 0
    @State private var showingClearConfirmation = false
    @State private var status = ""

    var body: some View {
        Form {
            Section("Lernsitzung") {
                Text("Die App sendet diese Zusammenfassung nicht an ein Backend.")
                    .foregroundStyle(.secondary)
                TextField("Zusammenfassung (max. 500 Zeichen)", text: $sessionSummary, axis: .vertical)
                    .lineLimit(3...6)
                    .onChange(of: sessionSummary) { value in
                        if value.count > 500 { sessionSummary = String(value.prefix(500)) }
                    }
                Button("Zusammenfassung speichern") {
                    status = sessionSummary.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                        ? "Keine Zusammenfassung gespeichert."
                        : "Auf diesem Gerät gespeichert."
                }
                Text(status).foregroundStyle(.secondary)
            }
            Section("Lernen") {
                Toggle("Lokales Feedback aktivieren", isOn: $learningEnabled)
                Picker("Antwortstil", selection: $responseStyle) {
                    Text("Kurz").tag("concise")
                    Text("Schritt für Schritt").tag("step_by_step")
                    Text("Ausführlich").tag("detailed")
                }
                .disabled(!learningEnabled)
                Text("Feedback: \(helpfulCount) hilfreich, \(unclearCount) unklar, \(correctionCount) Korrekturen")
                    .foregroundStyle(.secondary)
                Button("Hilfreich") { if learningEnabled { helpfulCount += 1 } }
                    .disabled(!learningEnabled)
                Button("Unklar") { if learningEnabled { unclearCount += 1 } }
                    .disabled(!learningEnabled)
                Button("Korrektur") { if learningEnabled { correctionCount += 1 } }
                    .disabled(!learningEnabled)
            }
            Section {
                Button("Lokale Lerndaten löschen", role: .destructive) {
                    showingClearConfirmation = true
                }
            }
        }
        .navigationTitle("Lernprofil")
        .confirmationDialog(
            "Alle lokalen Lerndaten löschen?",
            isPresented: $showingClearConfirmation,
            titleVisibility: .visible
        ) {
            Button("Löschen", role: .destructive) {
                learningEnabled = false
                responseStyle = "concise"
                sessionSummary = ""
                helpfulCount = 0
                unclearCount = 0
                correctionCount = 0
                status = "Lokale Lerndaten gelöscht."
            }
            Button("Abbrechen", role: .cancel) {}
        } message: {
            Text("Diese Aktion kann nicht rückgängig gemacht werden.")
        }
    }
}

private struct DefenseSupportView: View {
    @State private var healthState: DefenseHealthState = .notConfigured
    @State private var showingEmailConfirmation = false
    @State private var emailMessage = ""
    @State private var question = ""
    @State private var answer = ""
    @State private var ticket: EscalationTicket?
    @State private var previousQuestion = ""
    @State private var questionRequestKey = UUID().uuidString
    @State private var manualRequestKey = "MANUAL_\(UUID().uuidString)"
    @State private var payloadCipher = SecureSupportPayloadCipher()
    @State private var supportQueue = SupportEscalationQueue(
        store: UserDefaultsSupportTicketStore(key: "support_queue_v1")
    )
    @Environment(\.openURL) private var openURL

    var body: some View {
        Form {
            Section("Offline-Support") {
                Text("Begrenzte Offline-Antworten sind verfügbar. Es gibt keinen KI-Dienst und keine automatische E-Mail-Übermittlung. Dies ist kein Notfallkanal.")
                    .foregroundStyle(.secondary)
                TextField("Kurze Supportfrage (max. 500 Zeichen)", text: $question, axis: .vertical)
                    .lineLimit(2...4)
                    .onChange(of: question) { value in
                        if value.count > 500 { question = String(value.prefix(500)) }
                        if value != previousQuestion {
                            previousQuestion = value
                            questionRequestKey = UUID().uuidString
                        }
                    }
                    .accessibilityHint("Ungeklärte Fragen bleiben verschlüsselt auf diesem Gerät. E-Mail-Entwürfe enthalten keinen Fragetext.")
                Button("Offline-Antwort anzeigen", action: answerQuestion)
                if !answer.isEmpty {
                    Text(answer).accessibilityAddTraits(.updatesFrequently)
                }
            }
            Section("Backend-Verbindung") {
                Text(stateDescription)
                    .accessibilityAddTraits(.updatesFrequently)
                Button("Verbindung prüfen", action: checkBackend)
                    .disabled(healthState == .checking)
            }
            Section("E-Mail-Support") {
                Text("Ungeklärte Fragen bleiben lokal verschlüsselt. Nach Bestätigung enthält der E-Mail-Entwurf nur eine zufällige Vorgangskennung, die App und feste Fehler- und Diagnosecodes, keinen Fragetext.")
                    .foregroundStyle(.secondary)
                Button("E-Mail-Entwurf öffnen") { showingEmailConfirmation = true }
                if let ticket {
                    Text("Vorgemerkt: \(ticket.id.uuidString). Versand ist nicht bestätigt.")
                        .font(.footnote)
                    if ticket.handoffState == .uncertain {
                        Text("Übergabestatus unklar. Prüfe zuerst die E-Mail-App, um doppelte Entwürfe zu vermeiden.")
                    }
                    if ticket.handoffState == .handedOff {
                        Text("An die E-Mail-App übergeben; dies bestätigt keinen Versand.")
                        Button("E-Mail wurde gesendet") { markTicketSent() }
                    }
                    Button("Lokalen Vorgang löschen", role: .destructive, action: deleteTicket)
                    Text("Löschen entfernt nur diesen lokalen Vorgang. Entwürfe oder gesendete E-Mails in der E-Mail-App werden nicht gelöscht oder zurückgerufen.")
                        .font(.footnote)
                }
            }
            if !emailMessage.isEmpty {
                Text(emailMessage).foregroundStyle(.secondary)
            }
        }
        .navigationTitle("Support")
        .onAppear(perform: loadTicket)
        .confirmationDialog(
            "E-Mail-Entwurf öffnen?",
            isPresented: $showingEmailConfirmation,
            titleVisibility: .visible
        ) {
            Button("E-Mail öffnen") { openSupportEmail() }
            Button("Abbrechen", role: .cancel) {}
        } message: {
            Text("Empfänger: n_nold@hotmail.com. Der Entwurf enthält nur eine zufällige Vorgangskennung, die App und feste Fehler- und Diagnosecodes. Frage, Lernprofil und Gesprächsdaten werden nicht übernommen. Nichts wird automatisch gesendet. Prüfe den Entwurf und sende selbst.")
        }
    }

    private var stateDescription: String {
        switch healthState {
        case .notConfigured: "Nicht konfiguriert. Es wurde keine Verbindung versucht."
        case .checking: "Verbindung wird geprüft …"
        case .ready: "Backend meldet Bereitschaft. Dies bestätigt keine KI-Verfügbarkeit."
        case .unavailable: "Backend nicht erreichbar oder Antwort ungültig. Erneut prüfen, wenn online."
        }
    }

    private func checkBackend() {
        healthState = .checking
        Task {
            let result = await DefenseHealthClient.check(
                baseURL: Bundle.main.object(forInfoDictionaryKey: "BackendBaseURL") as? String ?? ""
            )
            healthState = result
            if result != .ready {
                let diagnostic = result == .notConfigured ? "NOT_CONFIGURED" : "UNAVAILABLE"
                if let encrypted = try? payloadCipher.encrypt("") {
                    enqueue(
                        issue: "BACKEND",
                        diagnostic: diagnostic,
                        requestKey: "BACKEND_\(diagnostic)",
                        encryptedPayload: encrypted
                    )
                }
            }
        }
    }

    private func answerQuestion() {
        guard !question.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            answer = "Bitte gib eine kurze Frage ein."
            return
        }
        let result = SupportAssistant.answer(question)
        answer = {
            switch result.code {
            case .backendHealth:
                "Der Verbindungstest prüft nur Backend-Erreichbarkeit, nicht die KI-Verfügbarkeit."
            case .privacy:
                "Fragen werden nur lokal beantwortet; ungeklärte Fragen bleiben lokal verschlüsselt. E-Mail-Entwürfe enthalten nach Bestätigung nur eine zufällige Vorgangskennung, die App und feste Fehler- und Diagnosecodes, keinen Fragetext."
            case .payment:
                "Zahlungsfragen können wir nicht bearbeiten. Wende dich an den Zahlungsanbieter oder Händler; sende keine Zahlungsdaten."
            case .troubleshooting:
                "Starte die App neu und wiederhole den Schritt. Prüfe bei Verbindungsproblemen den Backend-Status. Bleibt der Fehler bestehen, beschreibe ihn im E-Mail-Entwurf."
            case .accountUnavailable:
                "Konten und Passwort-Wiederherstellung sind derzeit nicht verfügbar. Sende niemals dein Passwort."
            case .unresolved:
                "Dafür gibt es keine verlässliche Offline-Antwort. Der Vorgang wird zur persönlichen Klärung vorgemerkt."
            }
        }()
        if result.escalationRequired {
            if let encrypted = try? payloadCipher.encrypt(question) {
                enqueue(
                    issue: result.code.rawValue.uppercased(),
                    diagnostic: "UNRESOLVED",
                    requestKey: questionRequestKey,
                    encryptedPayload: encrypted
                )
            } else {
                emailMessage = "Die Anfrage konnte nicht sicher verschlüsselt und vorgemerkt werden."
            }
        }
    }

    private func enqueue(
        issue: String,
        diagnostic: String,
        requestKey: String,
        encryptedPayload: String
    ) {
        do {
            ticket = try supportQueue.enqueue(
                app: .niknoligDefense,
                requestKey: requestKey,
                issueCode: issue,
                diagnosticCode: diagnostic,
                encryptedPayload: encryptedPayload
            )
        } catch {
            emailMessage = "Die Anfrage konnte nicht sicher vorgemerkt werden. Es wurde keine E-Mail geöffnet."
        }
    }

    private func loadTicket() {
        ticket = try? supportQueue.tickets().last(where: { $0.app == .niknoligDefense })
    }

    private func openSupportEmail() {
        if ticket == nil {
            guard let encrypted = try? payloadCipher.encrypt(question) else {
                emailMessage = "Die Anfrage konnte nicht sicher verschlüsselt und vorgemerkt werden."
                return
            }
            enqueue(
                issue: "MANUAL_REQUEST",
                diagnostic: healthState == .notConfigured ? "NOT_CONFIGURED" : "NO_MATCH",
                requestKey: manualRequestKey,
                encryptedPayload: encrypted
            )
        }
        guard let currentTicket = ticket, currentTicket.handoffState == .ready else {
            emailMessage = ticket?.handoffState == .handedOff
                ? "Dieser Vorgang wurde bereits übergeben. Prüfe die E-Mail-App, um doppelte Entwürfe zu vermeiden."
                : "Übergabestatus unklar oder Anfrage nicht vorgemerkt. Prüfe zuerst die E-Mail-App."
            return
        }
        guard currentTicket.canShareMetadata(for: .niknoligDefense) else {
            emailMessage = "Die Vorgangsmetadaten sind ungültig. Nichts wurde geöffnet."
            return
        }
        guard let started = try? supportQueue.beginHandoff(currentTicket.id) else {
            emailMessage = currentTicket.handoffAttempts >= SupportEscalationQueue.maxHandoffAttempts
                ? "Versuche ausgeschöpft. Schreibe manuell an n_nold@hotmail.com und nenne \(currentTicket.id.uuidString)."
                : "Die Warteschlange konnte nicht sicher gespeichert werden."
            return
        }
        var components = URLComponents()
        components.scheme = "mailto"
        components.path = "n_nold@hotmail.com"
        components.queryItems = [
            URLQueryItem(name: "subject", value: "NIKNOLIG Defense Support · \(started.id.uuidString)"),
            URLQueryItem(
                name: "body",
                value: """
                Vorgangskennung: \(started.id.uuidString)
                App: \(started.app.rawValue)
                Fehlerklasse: \(started.issueCode)
                Diagnose: \(started.diagnosticCode)

                Kein Fragetext oder Gesprächsinhalt wurde übernommen. Du musst diese E-Mail selbst prüfen und senden.
                """
            )
        ]
        guard let url = components.url else {
            ticket = try? supportQueue.finishHandoff(started.id, launched: false)
            emailMessage = "Der E-Mail-Entwurf konnte nicht vorbereitet werden."
            return
        }
        openURL(url) { accepted in
            let updated = try? supportQueue.finishHandoff(started.id, launched: accepted)
            guard ticket?.id == started.id else { return }
            ticket = updated
            emailMessage = accepted
                ? "E-Mail-App geöffnet. Nichts wurde gesendet. Prüfe den Entwurf und sende selbst."
                : "Keine E-Mail-App verfügbar. Der Vorgang bleibt vorgemerkt und kann begrenzt erneut versucht werden."
        }
    }

    private func markTicketSent() {
        guard let ticket, (try? supportQueue.complete(ticket.id)) == true else { return }
        self.ticket = nil
        loadTicket()
        emailMessage = "Vorgang auf diesem Gerät abgeschlossen."
    }

    private func deleteTicket() {
        guard let ticket else { return }
        do {
            guard try supportQueue.remove(ticket.id, app: .niknoligDefense) else { return }
            self.ticket = nil
            question = ""
            answer = ""
            loadTicket()
            emailMessage = "Lokaler Vorgang gelöscht. Externe E-Mail-Entwürfe und gesendete E-Mails wurden nicht gelöscht oder zurückgerufen."
        } catch {
            emailMessage = "Der lokale Vorgang konnte nicht gelöscht werden."
        }
    }
}

private enum DefenseHealthClient {
    static func check(baseURL: String) async -> DefenseHealthState {
        let value = baseURL.trimmingCharacters(in: .whitespacesAndNewlines)
        guard var components = URLComponents(string: value),
              components.scheme?.lowercased() == "https",
              let host = components.host?.lowercased().trimmingCharacters(in: CharacterSet(charactersIn: ".")),
              !host.isEmpty,
              components.user == nil,
              components.password == nil,
              components.path.isEmpty || components.path == "/",
              components.query == nil,
              components.fragment == nil,
              host != "localhost",
              !host.hasSuffix(".localhost"),
              host != "backend.invalid",
              !host.hasSuffix(".invalid"),
              host != "127.0.0.1",
              host != "::1" else {
            return .notConfigured
        }
        components.path = "/health/ready"
        guard let url = components.url else { return .notConfigured }
        return await withCheckedContinuation { continuation in
            let probe = DefenseHealthProbe { state in continuation.resume(returning: state) }
            let configuration = URLSessionConfiguration.ephemeral
            configuration.timeoutIntervalForRequest = 5
            configuration.timeoutIntervalForResource = 5
            let session = URLSession(configuration: configuration, delegate: probe, delegateQueue: nil)
            probe.session = session
            session.dataTask(with: url).resume()
        }
    }
}

private final class DefenseHealthProbe: NSObject, URLSessionDataDelegate, URLSessionTaskDelegate {
    var session: URLSession?
    private let completion: (DefenseHealthState) -> Void
    private var response: HTTPURLResponse?
    private var data = Data()
    private var completed = false

    init(completion: @escaping (DefenseHealthState) -> Void) {
        self.completion = completion
    }

    func urlSession(
        _ session: URLSession,
        task: URLSessionTask,
        willPerformHTTPRedirection response: HTTPURLResponse,
        newRequest request: URLRequest,
        completionHandler: @escaping (URLRequest?) -> Void
    ) {
        completionHandler(nil)
    }

    func urlSession(
        _ session: URLSession,
        dataTask: URLSessionDataTask,
        didReceive response: URLResponse,
        completionHandler: @escaping (URLSession.ResponseDisposition) -> Void
    ) {
        guard let http = response as? HTTPURLResponse,
              http.statusCode == 200,
              http.mimeType?.lowercased() == "application/json" else {
            complete(.unavailable)
            completionHandler(.cancel)
            return
        }
        self.response = http
        completionHandler(.allow)
    }

    func urlSession(_ session: URLSession, dataTask: URLSessionDataTask, didReceive chunk: Data) {
        guard data.count + chunk.count <= 4_096 else {
            complete(.unavailable)
            dataTask.cancel()
            return
        }
        data.append(chunk)
    }

    func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
        guard !completed else { return }
        if let error = error as? URLError, error.code == .timedOut {
            complete(.unavailable)
            return
        }
        guard error == nil,
              response?.statusCode == 200,
              let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              object.count == 1,
              object["status"] as? String == "ready" else {
            complete(.unavailable)
            return
        }
        complete(.ready)
    }

    private func complete(_ state: DefenseHealthState) {
        guard !completed else { return }
        completed = true
        completion(state)
        session?.finishTasksAndInvalidate()
    }
}

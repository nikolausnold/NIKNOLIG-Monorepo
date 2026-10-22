import Foundation
import SwiftUI

@main
struct NIKNOLIGApp: App {
    var body: some Scene {
        WindowGroup {
            NIKNOLIGHomeView()
        }
    }
}

private enum NIKNOLIGRoute: Hashable {
    case assistant
    case profile
    case support
}

private enum NIKNOLIGHealthState: Equatable {
    case notConfigured
    case checking
    case ready
    case unavailable
}

private struct NIKNOLIGHomeView: View {
    @State private var path: [NIKNOLIGRoute] = []

    var body: some View {
        NavigationStack(path: $path) {
            List {
                Section {
                    Text("Vorschau – Geräteverbindungen und produktive Funktionen sind nicht verfügbar.")
                        .foregroundStyle(.secondary)
                }
                Section("NIKNOLIG") {
                    NavigationLink("Elektro-Engel Vorschau", value: NIKNOLIGRoute.assistant)
                    NavigationLink("Lernprofil", value: NIKNOLIGRoute.profile)
                    NavigationLink("Support", value: NIKNOLIGRoute.support)
                }
            }
            .navigationTitle("NIKNOLIG")
            .navigationDestination(for: NIKNOLIGRoute.self) { route in
                switch route {
                case .assistant:
                    NIKNOLIGAssistantView()
                case .profile:
                    NIKNOLIGProfileView()
                case .support:
                    NIKNOLIGSupportView()
                }
            }
        }
        .tint(Color(red: 0.66, green: 0.87, blue: 0.24))
    }
}

private struct NIKNOLIGAssistantView: View {
    @State private var request = ""
    @State private var status = "Die Vorschau sendet keine Anfrage und erzeugt keine KI-Antwort."

    var body: some View {
        Form {
            Section("Elektro-Engel") {
                Text("Lokale Vorschau. Es gibt keine Geräteaktionen oder Backend-Verbindung.")
                    .foregroundStyle(.secondary)
                TextField("Anfrage", text: $request, axis: .vertical)
                    .lineLimit(3...6)
                Button("Anfrage prüfen") {
                    status = request.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                        ? "Bitte gib zuerst eine Anfrage ein."
                        : "KI-Support ist deaktiviert. Die Anfrage wurde nicht gesendet."
                }
                Text(status)
                    .accessibilityAddTraits(.updatesFrequently)
            }
        }
        .navigationTitle("Elektro-Engel")
    }
}

private struct NIKNOLIGProfileView: View {
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
                Text("Vorschau des Antwortstils: \(stylePreview)")
                    .foregroundStyle(.secondary)
                Text("Feedback: \(helpfulCount) hilfreich, \(unclearCount) unklar, \(correctionCount) Korrekturen")
                    .foregroundStyle(.secondary)
                Button("Hilfreich", action: { recordFeedback(.helpful) })
                    .disabled(!learningEnabled)
                Button("Unklar", action: { recordFeedback(.unclear) })
                    .disabled(!learningEnabled)
                Button("Korrektur", action: { recordFeedback(.correction) })
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
            Button("Löschen", role: .destructive, action: clearLearningData)
            Button("Abbrechen", role: .cancel) {}
        } message: {
            Text("Diese Aktion kann nicht rückgängig gemacht werden.")
        }
    }

    private var stylePreview: String {
        switch responseStyle {
        case "step_by_step":
            return "Schrittweise, lokale Vorschau."
        case "detailed":
            return "Ausführliche, lokale Vorschau."
        default:
            return "Kurze, lokale Vorschau."
        }
    }

    private enum FeedbackKey {
        case helpful, unclear, correction
    }

    private func recordFeedback(_ key: FeedbackKey) {
        switch key {
        case .helpful: helpfulCount += 1
        case .unclear: unclearCount += 1
        case .correction: correctionCount += 1
        }
    }

    private func clearLearningData() {
        learningEnabled = false
        responseStyle = "concise"
        sessionSummary = ""
        helpfulCount = 0
        unclearCount = 0
        correctionCount = 0
        status = "Lokale Lerndaten gelöscht."
    }
}

private struct NIKNOLIGSupportView: View {
    @State private var healthState: NIKNOLIGHealthState = .notConfigured
    @State private var showingEmailConfirmation = false
    @State private var emailMessage = ""
    @Environment(\.openURL) private var openURL

    var body: some View {
        Form {
            Section("Backend-Verbindung") {
                Text(stateDescription)
                    .accessibilityAddTraits(.updatesFrequently)
                Button("Verbindung prüfen", action: checkBackend)
                    .disabled(healthState == .checking)
            }
            Section("E-Mail-Support") {
                Text("Es wird ein E-Mail-Entwurf geöffnet. Die App sendet keine E-Mail.")
                    .foregroundStyle(.secondary)
                Button("E-Mail-Entwurf öffnen") {
                    showingEmailConfirmation = true
                }
            }
            if !emailMessage.isEmpty {
                Text(emailMessage).foregroundStyle(.secondary)
            }
        }
        .navigationTitle("Support")
        .confirmationDialog(
            "E-Mail-Entwurf öffnen?",
            isPresented: $showingEmailConfirmation,
            titleVisibility: .visible
        ) {
            Button("E-Mail öffnen") { openSupportEmail() }
            Button("Abbrechen", role: .cancel) {}
        } message: {
            Text("Der Entwurf wird an die Supportadresse übergeben. Nichts wird automatisch gesendet.")
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
            healthState = await NIKNOLIGHealthClient.check(
                baseURL: Bundle.main.object(forInfoDictionaryKey: "BackendBaseURL") as? String ?? ""
            )
        }
    }

    private func openSupportEmail() {
        var components = URLComponents()
        components.scheme = "mailto"
        components.path = "n_nold@hotmail.com"
        components.queryItems = [
            URLQueryItem(name: "subject", value: "NIKNOLIG Support"),
            URLQueryItem(name: "body", value: "Bitte beschreibe dein Anliegen. Füge keine Zugangsdaten oder sensiblen Informationen bei.")
        ]
        guard let url = components.url else {
            emailMessage = "Der E-Mail-Entwurf konnte nicht vorbereitet werden."
            return
        }
        openURL(url) { accepted in
            emailMessage = accepted
                ? "E-Mail-App geöffnet. Der Versand erfolgt nicht automatisch."
                : "Keine E-Mail-App verfügbar. Bitte wende dich an n_nold@hotmail.com."
        }
    }
}

private enum NIKNOLIGHealthClient {
    static func check(baseURL: String) async -> NIKNOLIGHealthState {
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
            let probe = NIKNOLIGHealthProbe { state in
                continuation.resume(returning: state)
            }
            let configuration = URLSessionConfiguration.ephemeral
            configuration.timeoutIntervalForRequest = 5
            configuration.timeoutIntervalForResource = 5
            let session = URLSession(configuration: configuration, delegate: probe, delegateQueue: nil)
            probe.session = session
            session.dataTask(with: url).resume()
        }
    }
}

private final class NIKNOLIGHealthProbe: NSObject, URLSessionDataDelegate, URLSessionTaskDelegate {
    var session: URLSession?
    private let completion: (NIKNOLIGHealthState) -> Void
    private var response: HTTPURLResponse?
    private var data = Data()
    private var completed = false

    init(completion: @escaping (NIKNOLIGHealthState) -> Void) {
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

    private func complete(_ state: NIKNOLIGHealthState) {
        guard !completed else { return }
        completed = true
        completion(state)
        session?.finishTasksAndInvalidate()
    }
}

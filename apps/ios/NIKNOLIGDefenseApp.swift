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
                    .onChange(of: sessionSummary) { _, value in
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
    @Environment(\.openURL) private var openURL

    var body: some View {
        Form {
            Section("KI-Support") {
                Text("KI-Support ist derzeit nicht freigegeben. Er ist kein Notfallkanal und ersetzt keine Notruf- oder Schutzfunktion.")
                    .foregroundStyle(.secondary)
            }
            Section("Backend-Verbindung") {
                Text(stateDescription)
                    .accessibilityAddTraits(.updatesFrequently)
                Button("Verbindung prüfen", action: checkBackend)
                    .disabled(healthState == .checking)
            }
            Section("E-Mail-Support") {
                Text("Es wird ein E-Mail-Entwurf geöffnet. Die App sendet keine E-Mail.")
                    .foregroundStyle(.secondary)
                Button("E-Mail-Entwurf öffnen") { showingEmailConfirmation = true }
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
            healthState = await DefenseHealthClient.check(
                baseURL: Bundle.main.object(forInfoDictionaryKey: "BackendBaseURL") as? String ?? ""
            )
        }
    }

    private func openSupportEmail() {
        var components = URLComponents()
        components.scheme = "mailto"
        components.path = "n_nold@hotmail.com"
        components.queryItems = [
            URLQueryItem(name: "subject", value: "NIKNOLIG Defense Support"),
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

import Foundation

enum ElectroEngelMode: String, CaseIterable, Identifiable, Sendable {
    case wordBreakdown = "Wort-Zerleger"
    case conventionScan = "Konventions-Scanner"
    case perspectiveShift = "Perspektiven-Wechsler"
    case factCheck = "Fakten- und Denkfehler-Prüfer"

    var id: String { rawValue }
}

enum ElectroEngelFailure: Sendable {
    case emptyInput
    case invalidInput
    case aiDisabled
    case providerUnavailable
    case timeout
}

struct ElectroEngelRequest: Sendable {
    let mode: ElectroEngelMode
    let text: String
    let refinement: String
}

struct ElectroEngelSection: Identifiable, Sendable {
    let heading: String
    let content: String
    var id: String { heading }
}

struct ElectroEngelResult: Sendable {
    let sections: [ElectroEngelSection]
    let uncertainty: String
    let sourceStatus: String
    let sources: [String]
}

enum ElectroEngelOutcome: Sendable {
    case success(ElectroEngelResult)
    case failure(ElectroEngelFailure)
}

enum ElectroEngelRemoteBoundary {
    static func unavailable() -> ElectroEngelOutcome {
        .failure(.aiDisabled)
    }

    static func failed(_ error: Error) -> ElectroEngelOutcome {
        if let urlError = error as? URLError, urlError.code == .timedOut {
            return .failure(.timeout)
        }
        return .failure(.providerUnavailable)
    }
}

enum ElectroEngelAnalyzer {
    private static let wordGlosses: [String: String] = [
        "mutter": "Kann eine Elternrolle, eine Anrede oder – je nach Zusammenhang – einen Fachbegriff bezeichnen.",
        "geld": "Ein Arbeitsbegriff für allgemein verwendete Tausch- und Wertaufbewahrungsmittel; genaue Definitionen unterscheiden sich.",
        "treue": "Kann Verlässlichkeit oder Beständigkeit in einer Beziehung, Bindung oder Aufgabe meinen.",
        "erfolg": "Kann das Erreichen eines Ziels oder eines bewerteten Ergebnisses meinen; wer den Maßstab setzt, ist entscheidend.",
        "freiheit": "Kann Handlungsspielraum oder Selbstbestimmung meinen; Rechte, Pflichten und tatsächliche Möglichkeiten setzen unterschiedliche Grenzen."
    ]

    static func analyze(_ request: ElectroEngelRequest) -> ElectroEngelOutcome {
        guard request.text.count <= 1_000, request.text.utf8.count <= 2_048,
              request.refinement.count <= 500,
              !hasDisallowedControls(request.text), !hasDisallowedControls(request.refinement) else {
            return .failure(.invalidInput)
        }
        let text = request.text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return .failure(.emptyInput) }

        let subject = request.refinement.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            ? text
            : "\(text)\n\nVertiefungsfrage: \(request.refinement)"
        let sections: [ElectroEngelSection]
        switch request.mode {
        case .wordBreakdown:
            sections = wordBreakdown(text, refinement: request.refinement)
        case .conventionScan:
            sections = conventionScan(subject)
        case .perspectiveShift:
            sections = perspectiveShift(subject)
        case .factCheck:
            sections = factCheck(subject)
        }
        return .success(ElectroEngelResult(
            sections: sections,
            uncertainty: "Sprachliche, regelbasierte Erstprüfung. Keine Wörterbuch-, Quellen- oder Faktenrecherche; Aussagen und Einordnungen können unvollständig sein.",
            sourceStatus: "Nicht geprüft; es wurde keine externe Quelle abgefragt.",
            sources: []
        ))
    }

    private static func hasDisallowedControls(_ text: String) -> Bool {
        text.unicodeScalars.contains {
            CharacterSet.controlCharacters.contains($0) &&
                $0 != "\n" && $0 != "\r" && $0 != "\t"
        }
    }

    private static func wordBreakdown(_ text: String, refinement: String) -> [ElectroEngelSection] {
        let key = text.lowercased().trimmingCharacters(in: CharacterSet(charactersIn: ".!?"))
        let gloss = wordGlosses[key]
            ?? "Für diesen Begriff liegt keine kuratierte Arbeitsfassung vor. Bedeutung und Gebrauch hängen vom Satz und Kontext ab."
        return [
            ElectroEngelSection(heading: "Wortbedeutung · Arbeitsfassung", content: gloss),
            ElectroEngelSection(heading: "Wortgeschichte", content: "Nicht geprüft. Ohne ein verlässliches etymologisches Wörterbuch oder einen historischen Beleg wird keine Herkunft behauptet."),
            ElectroEngelSection(heading: "Kulturelle Prägung", content: "Gebrauch und Wertung können sich zwischen Gemeinschaften, Zeiten und Lebensbereichen unterscheiden. Eine konkrete Zuordnung wurde nicht recherchiert."),
            ElectroEngelSection(
                heading: "Persönliche Interpretation",
                content: refinement.isEmpty ? "Welche Erfahrung, Erwartung oder Wertung verbindest du persönlich mit „\(text)“?" : refinement
            )
        ]
    }

    private static func conventionScan(_ text: String) -> [ElectroEngelSection] {
        let normalized = text.lowercased()
        var matches: [String] = []
        if containsAny(normalized, ["messbar", "misst", "beträgt", "gezählt", "beobachtet", "nachweisbar", "experiment"]) {
            matches.append("Empirisch überprüfbar: Der Wortlaut verweist auf Beobachtung, Messung oder einen möglichen Nachweis; konkrete Daten wurden nicht geprüft.")
        }
        if containsAny(normalized, ["bedeutet", "definition", "definiert als", "unter ... versteht"]) {
            matches.append("Definitorisch: Die Aussage scheint einen Begriff festzulegen oder zu erläutern; damit ist die Definition nicht automatisch allgemein anerkannt.")
        }
        if containsAny(normalized, ["üblich", "tradition", "normal", "gesellschaftlich", "gesetzlich", "vereinbart", "konvention"]) {
            matches.append("Gesellschaftlich vereinbart: Die Formulierung deutet auf eine Regel, Erwartung oder Praxis hin; Reichweite und tatsächliche Zustimmung bleiben offen.")
        }
        if containsAny(normalized, ["sollte", "muss", "darf nicht", "richtig", "falsch", "gerecht", "verpflichtet"]) {
            matches.append("Normativ: Die Aussage enthält ein Sollen, Dürfen oder eine Bewertung; sie braucht eine benannte Begründung oder Wertgrundlage.")
        }
        if containsAny(normalized, ["ich finde", "für mich", "meiner meinung", "ich glaube", "fühlt sich"]) {
            matches.append("Persönlich: Der Wortlaut markiert eine eigene Einschätzung oder Erfahrung; sie belegt keine allgemeine Tatsache.")
        }
        if matches.isEmpty {
            matches.append("Noch nicht eindeutig einzuordnen: Im Wortlaut fehlen klare Hinweise auf Prüfbarkeit, Definition, Vereinbarung, Wertung oder persönliche Sicht.")
        }
        return [
            ElectroEngelSection(heading: "Mögliche Einordnungen", content: matches.joined(separator: "\n\n")),
            ElectroEngelSection(heading: "Begründung und Grenze", content: "Die Zuordnung folgt nur erkennbaren Sprachhinweisen. Eine Aussage kann zugleich mehrere Kategorien enthalten; die Einordnung bestätigt weder ihre Wahrheit noch ihre Geltung.")
        ]
    }

    private static func perspectiveShift(_ text: String) -> [ElectroEngelSection] {
        let absolute = containsAny(text.lowercased(), ["immer", "niemals", "alle ", "jeder ", "niemand", "ausschließlich", "nur "])
        let counterpoint = absolute
            ? "Gegenfrage: Gibt es einen konkreten Gegenfall oder eine Gruppe, für die die Aussage nicht gilt?"
            : "Gegenfrage: Unter welchen Bedingungen würde eine vernünftige Person zu einer anderen Einschätzung kommen?"
        return [
            ElectroEngelSection(heading: "Historische Perspektive", content: "Frage, wie sich Bedeutung, Bedingungen und Folgen über verschiedene Zeiten verändert haben könnten. Ohne konkrete Quellen wird keine historische Entwicklung behauptet."),
            ElectroEngelSection(heading: "Kulturelle Perspektive", content: "Frage, welche unterschiedlichen Erfahrungen, Rollen oder örtlichen Gepflogenheiten die Sicht beeinflussen könnten. Es wird keiner konkreten Kultur eine Position zugeschrieben."),
            ElectroEngelSection(heading: "Philosophische Perspektive", content: "Prüfe, welche Werte oder Begriffe vorausgesetzt werden und ob individuelle Freiheit, gemeinsame Pflichten und Folgen unterschiedlich gewichtet werden."),
            ElectroEngelSection(heading: "Gemeinsamkeiten, Unterschiede und Gegenargument", content: "Gemeinsamkeit: Jede Perspektive kann nach Voraussetzungen und Folgen fragen. Unterschiede entstehen durch Maßstab und Gewichtung; alternative Sichtweisen sind keine bewiesenen Tatsachen.\n\n\(counterpoint)\n\nAusgangspunkt: „\(text)“")
        ]
    }

    private static func factCheck(_ text: String) -> [ElectroEngelSection] {
        let sentences = text.split(whereSeparator: { ".!?".contains($0) }).map(String.init).filter { !$0.isEmpty }
        let claims = sentences.map { sentence -> String in
            let lower = sentence.lowercased()
            var labels: [String] = []
            if containsAny(lower, ["ich glaube", "ich finde", "meiner meinung", "für mich"]) {
                labels.append("Meinung / persönliche Einschätzung")
            }
            if containsAny(lower, ["vielleicht", "möglicherweise", "vermutlich", "könnte", "wahrscheinlich"]) {
                labels.append("Hypothese / Vermutung")
            }
            if containsAny(lower, ["also", "daher", "deshalb", "folglich", "somit"]) {
                labels.append("Schlussfolgerung")
            }
            if labels.isEmpty { labels.append("Möglicherweise überprüfbare Tatsachenbehauptung") }
            return "• \(labels.joined(separator: " + ")): \(sentence)"
        }
        var flags: [String] = []
        if containsAny(text.lowercased(), ["immer", "niemals", "alle ", "jeder ", "niemand", "keiner "]) {
            flags.append("Pauschalisierungssignal: absolute Wörter wie „alle“, „immer“ oder „niemand“ verlangen Gegenbeispiele und eine klar begrenzte Gruppe.")
        }
        if text.range(of: #"\b(ist|sind|hat|haben)\b[^.!?]{0,100}\b(und|aber)\b[^.!?]{0,50}\b(nicht|kein|keine|keiner)\b"#, options: .regularExpression) != nil {
            flags.append("Möglicher Widerspruch: der Satz verbindet eine Behauptung und eine Verneinung. Prüfe, ob wirklich derselbe Gegenstand, Zeitraum und Sinn gemeint ist.")
        }
        if flags.isEmpty {
            flags.append("Keine dieser einfachen Muster wurde eindeutig erkannt. Das beweist weder Widerspruchsfreiheit noch Richtigkeit.")
        }
        return [
            ElectroEngelSection(heading: "Aussagenarten · vorläufig", content: claims.joined(separator: "\n")),
            ElectroEngelSection(heading: "Denkfehler-Signale", content: flags.joined(separator: "\n\n")),
            ElectroEngelSection(heading: "Fakten- und Quellenstatus", content: "Keine externe Quelle wurde abgefragt. Hypothesen, Meinungen und Schlussfolgerungen sind nicht als bestätigte Fakten zu lesen.")
        ]
    }

    private static func containsAny(_ text: String, _ cues: [String]) -> Bool {
        cues.contains(where: text.contains)
    }
}

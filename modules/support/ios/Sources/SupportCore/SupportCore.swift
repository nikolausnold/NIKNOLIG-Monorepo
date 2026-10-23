import Foundation
#if canImport(CryptoKit) && canImport(Security)
import CryptoKit
import Security
#endif

public enum SupportApp: String, Codable {
    case niknolig
    case niknoligDefense = "niknolig-defense"
}

public enum SupportAnswerCode: String {
    case backendHealth
    case privacy
    case payment
    case troubleshooting
    case accountUnavailable
    case unresolved
}

public struct SupportAnswer {
    public let code: SupportAnswerCode
    public let escalationRequired: Bool

    public init(code: SupportAnswerCode, escalationRequired: Bool) {
        self.code = code
        self.escalationRequired = escalationRequired
    }
}

public enum SupportDiagnostic: String, Codable {
    case ready
    case notConfigured
    case invalidResponse
    case timedOut
    case networkError
    case httpError

    public var escalationRequired: Bool { self != .ready }
}

public enum SupportAssistant {
    public static let maxQuestionBytes = 2_048

    public static func answer(_ question: String) -> SupportAnswer {
        guard !question.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              question.lengthOfBytes(using: .utf8) <= maxQuestionBytes else {
            return SupportAnswer(code: .unresolved, escalationRequired: true)
        }
        let words = Set(
            question.lowercased().split { !$0.isLetter && !$0.isNumber }.map(String.init)
        )
        if containsAny(words, "passwort", "password", "login", "konto", "account") {
            return SupportAnswer(code: .accountUnavailable, escalationRequired: true)
        }
        if containsAny(words, "zahlung", "preis", "payment", "rechnung", "billing") {
            return SupportAnswer(code: .payment, escalationRequired: false)
        }
        if containsAny(words, "datenschutz", "privacy", "daten", "data") {
            return SupportAnswer(code: .privacy, escalationRequired: false)
        }
        if containsAny(words, "backend", "verbindung", "connection", "server", "ki", "ai") {
            return SupportAnswer(code: .backendHealth, escalationRequired: false)
        }
        if containsAny(words, "fehler", "problem", "funktioniert", "crash", "störung", "issue", "error") {
            return SupportAnswer(code: .troubleshooting, escalationRequired: false)
        }
        return SupportAnswer(code: .unresolved, escalationRequired: true)
    }

    private static func containsAny(_ words: Set<String>, _ values: String...) -> Bool {
        values.contains { words.contains($0) }
    }
}

public enum HandoffState: String, Codable {
    case ready
    case uncertain
    case handedOff
}

public struct EscalationTicket: Codable, Equatable {
    public let id: UUID
    public let app: SupportApp
    public let requestKey: String
    public let issueCode: String
    public let diagnosticCode: String
    public let encryptedPayload: String
    public let createdAtMilliseconds: Int64
    public var handoffAttempts: Int
    public var handoffState: HandoffState

    public func canShareMetadata(for expectedApp: SupportApp) -> Bool {
        app == expectedApp &&
            ["BACKENDHEALTH", "PRIVACY", "PAYMENT", "TROUBLESHOOTING",
             "ACCOUNTUNAVAILABLE", "UNRESOLVED", "BACKEND", "MANUAL_REQUEST"].contains(issueCode) &&
            ["READY", "NOT_CONFIGURED", "INVALID_RESPONSE", "TIMED_OUT", "NETWORK_ERROR",
             "HTTP_ERROR", "UNAVAILABLE", "UNRESOLVED", "NO_MATCH"].contains(diagnosticCode)
    }

    public init(
        id: UUID = UUID(),
        app: SupportApp,
        requestKey: String,
        issueCode: String,
        diagnosticCode: String,
        encryptedPayload: String,
        createdAtMilliseconds: Int64 = Int64(Date().timeIntervalSince1970 * 1_000),
        handoffAttempts: Int = 0,
        handoffState: HandoffState = .ready
    ) {
        self.id = id
        self.app = app
        self.requestKey = requestKey
        self.issueCode = issueCode
        self.diagnosticCode = diagnosticCode
        self.encryptedPayload = encryptedPayload
        self.createdAtMilliseconds = createdAtMilliseconds
        self.handoffAttempts = handoffAttempts
        self.handoffState = handoffState
    }
}

public protocol SupportTicketStore {
    func load() throws -> [EscalationTicket]
    func save(_ tickets: [EscalationTicket]) throws
}

public protocol SupportPayloadCipher {
    func encrypt(_ plaintext: String) throws -> String
    func decrypt(_ ciphertext: String) throws -> String
}

#if canImport(CryptoKit) && canImport(Security)
public struct SecureSupportPayloadCipher: SupportPayloadCipher {
    private let service: String

    public init(service: String = "org.niknolig.support.queue.v1") {
        self.service = service
    }

    public func encrypt(_ plaintext: String) throws -> String {
        let box = try AES.GCM.seal(Data(plaintext.utf8), using: key())
        guard let combined = box.combined else { throw SupportQueueError.encryptionFailed }
        return combined.base64EncodedString()
    }

    public func decrypt(_ ciphertext: String) throws -> String {
        guard let data = Data(base64Encoded: ciphertext) else {
            throw SupportQueueError.encryptionFailed
        }
        let box = try AES.GCM.SealedBox(combined: data)
        let plaintext = try AES.GCM.open(box, using: key())
        guard let result = String(data: plaintext, encoding: .utf8) else {
            throw SupportQueueError.encryptionFailed
        }
        return result
    }

    private func key() throws -> SymmetricKey {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: "payload-key",
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        var result: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        if status == errSecSuccess, let data = result as? Data {
            return SymmetricKey(data: data)
        }
        guard status == errSecItemNotFound else { throw SupportQueueError.encryptionFailed }

        let newKey = SymmetricKey(size: .bits256)
        let data = newKey.withUnsafeBytes { Data($0) }
        let addQuery: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: "payload-key",
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly,
            kSecValueData as String: data
        ]
        let addStatus = SecItemAdd(addQuery as CFDictionary, nil)
        guard addStatus == errSecSuccess || addStatus == errSecDuplicateItem else {
            throw SupportQueueError.encryptionFailed
        }
        return try key()
    }
}
#endif

public final class UserDefaultsSupportTicketStore: SupportTicketStore {
    private let defaults: UserDefaults
    private let key: String

    public init(defaults: UserDefaults = .standard, key: String = "support_queue_v1") {
        self.defaults = defaults
        self.key = key
    }

    public func load() throws -> [EscalationTicket] {
        guard let data = defaults.data(forKey: key) else { return [] }
        return try JSONDecoder().decode([EscalationTicket].self, from: data)
    }

    public func save(_ tickets: [EscalationTicket]) throws {
        let data = try JSONEncoder().encode(tickets)
        defaults.set(data, forKey: key)
    }
}

public final class SupportEscalationQueue {
    public static let maxTickets = 20
    public static let maxHandoffAttempts = 3

    private let store: SupportTicketStore
    private let clock: () -> Int64

    public init(
        store: SupportTicketStore,
        clock: @escaping () -> Int64 = { Int64(Date().timeIntervalSince1970 * 1_000) }
    ) {
        self.store = store
        self.clock = clock
    }

    public func enqueue(
        app: SupportApp,
        requestKey: String,
        issueCode: String,
        diagnosticCode: String,
        encryptedPayload: String
    ) throws -> EscalationTicket {
        guard Self.validRequestKey(requestKey),
              Self.validCode(issueCode),
              Self.validCode(diagnosticCode),
              Self.validPayload(encryptedPayload) else {
            throw SupportQueueError.invalidCode
        }
        var tickets = try store.load()
        if let existing = tickets.first(where: {
            $0.app == app && $0.requestKey == requestKey
        }) {
            return existing
        }
        guard tickets.count < Self.maxTickets else { throw SupportQueueError.full }
        let ticket = EscalationTicket(
            app: app,
            requestKey: requestKey,
            issueCode: issueCode,
            diagnosticCode: diagnosticCode,
            encryptedPayload: encryptedPayload,
            createdAtMilliseconds: clock()
        )
        tickets.append(ticket)
        try store.save(tickets)
        return ticket
    }

    public func tickets() throws -> [EscalationTicket] {
        try store.load()
    }

    public func beginHandoff(_ ticketID: UUID) throws -> EscalationTicket? {
        var tickets = try store.load()
        guard let index = tickets.firstIndex(where: { $0.id == ticketID }) else { return nil }
        guard tickets[index].handoffState == .ready,
              tickets[index].handoffAttempts < Self.maxHandoffAttempts else { return nil }
        tickets[index].handoffAttempts += 1
        tickets[index].handoffState = .uncertain
        try store.save(tickets)
        return tickets[index]
    }

    public func finishHandoff(_ ticketID: UUID, launched: Bool) throws -> EscalationTicket? {
        var tickets = try store.load()
        guard let index = tickets.firstIndex(where: { $0.id == ticketID }),
              tickets[index].handoffState == .uncertain else { return nil }
        tickets[index].handoffState = launched ? .handedOff : .ready
        try store.save(tickets)
        return tickets[index]
    }

    public func complete(_ ticketID: UUID) throws -> Bool {
        var tickets = try store.load()
        guard tickets.contains(where: { $0.id == ticketID && $0.handoffState == .handedOff }) else {
            return false
        }
        tickets.removeAll { $0.id == ticketID }
        try store.save(tickets)
        return true
    }

    public func remove(_ ticketID: UUID, app: SupportApp) throws -> Bool {
        let tickets = try store.load()
        let remaining = tickets.filter { !($0.id == ticketID && $0.app == app) }
        guard remaining.count != tickets.count else { return false }
        try store.save(remaining)
        return true
    }

    private static func validCode(_ code: String) -> Bool {
        !code.isEmpty && code.count <= 48 &&
            code.unicodeScalars.allSatisfy {
                CharacterSet(charactersIn: "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_").contains($0)
            }
    }

    private static func validRequestKey(_ key: String) -> Bool {
        !key.isEmpty && key.count <= 128 &&
            key.unicodeScalars.allSatisfy {
                CharacterSet(charactersIn: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-").contains($0)
            }
    }

    private static func validPayload(_ payload: String) -> Bool {
        !payload.isEmpty && payload.utf8.count <= 8_192 &&
            payload.unicodeScalars.allSatisfy {
                CharacterSet(charactersIn: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=_-").contains($0)
            }
    }
}

public enum SupportQueueError: Error {
    case invalidCode
    case full
    case encryptionFailed
}

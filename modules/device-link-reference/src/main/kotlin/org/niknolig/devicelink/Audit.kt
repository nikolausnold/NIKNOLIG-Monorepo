package org.niknolig.devicelink

enum class AuditType {
    PAIRING_STARTED,
    PAIRING_COMPLETED,
    PAIRING_FAILED,
    AUTH_SUCCEEDED,
    AUTH_FAILED,
    CONSENT_GRANTED,
    CONSENT_REVOKED,
    PEER_REVOKED,
    AUTHORIZATION_DENIED,
    SESSION_ERROR,
}

/** Closed set of result codes; free text is impossible by construction. */
enum class AuditResult {
    OK, TOKEN_INVALID, TOKEN_EXPIRED, TOKEN_REUSED, UNKNOWN_PEER, BAD_SIGNATURE, REPLAY,
    VERSION_UNSUPPORTED, SCOPE_MISMATCH, USER_DECLINED, NO_CONSENT, CONSENT_EXPIRED,
    PEER_REVOKED, WRONG_DIRECTION, SESSION_INVALID, CONNECTION_LOST, MALFORMED,
}

/** Only a type, a time, a pseudonymous peer reference and a result code are recorded. */
data class AuditEvent(val type: AuditType, val timeMillis: Long, val peerRef: String?, val result: AuditResult)

interface AuditSink {
    fun record(type: AuditType, peer: DeviceId?, result: AuditResult)
}

/**
 * Bounded, age-limited in-memory audit log. Retention values are proposals
 * pending the audit/deletion policy approval (D-xx); persistence is not
 * implemented and must not be enabled before that approval.
 */
class InMemoryAuditLog(
    private val clock: Clock,
    private val maxEvents: Int = 200,
    private val maxAgeMillis: Long = 30L * 24 * 60 * 60 * 1000,
) : AuditSink {
    private val events = ArrayDeque<AuditEvent>()

    override fun record(type: AuditType, peer: DeviceId?, result: AuditResult) {
        prune()
        events.addLast(AuditEvent(type, clock.nowMillis(), peer?.auditRef(), result))
        while (events.size > maxEvents) events.removeFirst()
    }

    fun snapshot(): List<AuditEvent> {
        prune()
        return events.toList()
    }

    fun clear() = events.clear()

    private fun prune() {
        val cutoff = clock.nowMillis() - maxAgeMillis
        while (events.isNotEmpty() && events.first().timeMillis < cutoff) events.removeFirst()
    }
}

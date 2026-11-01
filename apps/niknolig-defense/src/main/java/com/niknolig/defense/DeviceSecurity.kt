package com.niknolig.defense

/** Result codes only; no URLs, tokens, payloads or other secrets are ever stored. */
internal enum class ConnectionCode { READY, NOT_CONFIGURED, INVALID_RESPONSE, TIMED_OUT, NETWORK_ERROR, HTTP_ERROR }

internal data class ConnectionFailure(val timeMillis: Long, val code: ConnectionCode)

internal data class ConnectionState(val lastSuccessMillis: Long?, val failures: List<ConnectionFailure>)

/**
 * Records user-initiated backend health checks. Failures are bounded and contain
 * only a timestamp and a result code. "Not configured" is a setup state, not a
 * failed attempt, and is therefore never logged as a failure.
 */
internal class ConnectionLog(private val persistence: TextPersistence) {
    fun state(): ConnectionState {
        var success: Long? = null
        val failures = mutableListOf<ConnectionFailure>()
        persistence.read().orEmpty().lineSequence().forEach { line ->
            val parts = line.split('|')
            val time = parts.getOrNull(1)?.toLongOrNull() ?: return@forEach
            when (parts.getOrNull(0)) {
                "S" -> success = time
                "F" -> parts.getOrNull(2)?.let { name ->
                    ConnectionCode.values().firstOrNull { it.name == name }
                }?.let { failures += ConnectionFailure(time, it) }
            }
        }
        return ConnectionState(success, failures.takeLast(MAX_FAILURES))
    }

    fun record(code: ConnectionCode, nowMillis: Long): Boolean {
        if (code == ConnectionCode.NOT_CONFIGURED) return true
        val current = state()
        val lines = mutableListOf<String>()
        val success = if (code == ConnectionCode.READY) nowMillis else current.lastSuccessMillis
        success?.let { lines += "S|$it" }
        val failures = if (code == ConnectionCode.READY) current.failures
        else (current.failures + ConnectionFailure(nowMillis, code)).takeLast(MAX_FAILURES)
        failures.forEach { lines += "F|${it.timeMillis}|${it.code.name}" }
        return persistence.write(lines.joinToString("\n"))
    }

    fun clear(): Boolean = persistence.write("")

    companion object {
        const val MAX_FAILURES = 20
    }
}

internal enum class PairingBlocker {
    SECURITYCHAIN_P0_NOT_APPROVED,
    TRANSPORT_NOT_SELECTED,
    PEER_IDENTITY_NOT_APPROVED,
    CONSENT_AND_REVOCATION_NOT_APPROVED,
    AUDIT_POLICY_NOT_APPROVED,
    TWO_DEVICE_ACCEPTANCE_MISSING,
}

internal sealed class PairingGate {
    data object Open : PairingGate()
    data class Blocked(val blockers: List<PairingBlocker>) : PairingGate()

    companion object {
        /**
         * Approvals documented in docs/device-link-security-design.md and
         * docs/securitychain-p0-specification.md are all still open. A blocker is
         * cleared only by adding the written approval here; the default is fail closed.
         */
        val APPROVED: Set<PairingBlocker> = emptySet()

        fun evaluate(approved: Set<PairingBlocker> = APPROVED): PairingGate {
            val open = PairingBlocker.values().filterNot { it in approved }
            return if (open.isEmpty()) Open else Blocked(open)
        }
    }
}

internal data class SecurityCheck(val id: SecurityCheckId, val passed: Boolean)

internal enum class SecurityCheckId { BACKUP_DISABLED, CLEARTEXT_BLOCKED, NOT_DEBUGGABLE, BACKEND_HTTPS, ONLY_INTERNET_PERMISSION }

internal data class SecurityOverview(
    val events: List<ConnectionFailure>,
    val failedChecks: List<SecurityCheckId>,
    val passedChecks: List<SecurityCheckId>,
    val blockers: List<PairingBlocker>,
) {
    companion object {
        fun build(checks: List<SecurityCheck>, state: ConnectionState, gate: PairingGate) = SecurityOverview(
            events = state.failures.asReversed(),
            failedChecks = checks.filterNot { it.passed }.map { it.id },
            passedChecks = checks.filter { it.passed }.map { it.id },
            blockers = (gate as? PairingGate.Blocked)?.blockers.orEmpty(),
        )
    }
}

package com.niknolig.app

internal enum class DeviceLinkState {
    IDLE,
    CONNECTING,
    CONNECTED,
    REVOKED,
    FAILED,
}

internal data class DeviceLinkPeer(
    val installationId: String,
    val appArea: String,
    val sessionId: String,
)

internal data class DeviceLinkMessage(
    val contractVersion: String,
    val messageId: String,
    val sessionId: String,
    val senderInstallationId: String,
    val senderAppArea: String,
    val recipientAppArea: String,
    val sequence: Long,
    val eventType: String,
    val issuedAtEpochSeconds: Long,
    val expiresAtEpochSeconds: Long,
    val nonce: String,
    val signature: ByteArray,
)

internal data class DeviceLinkTransportEvidence(
    val sessionId: String,
    val peerInstallationId: String,
    val encrypted: Boolean,
    val mitmProtected: Boolean,
)

internal interface DeviceLinkBleTransport {
    fun connect(peer: DeviceLinkPeer, onResult: (DeviceLinkTransportEvidence?) -> Unit)
    fun disconnect()
}

internal interface DeviceLinkSecurityPolicy {
    fun verifyPeerIdentity(peer: DeviceLinkPeer, localAppArea: String): Boolean
    fun verifyPeerConsent(peer: DeviceLinkPeer, localAppArea: String): Boolean
    fun verifyTransportEvidence(
        peer: DeviceLinkPeer,
        evidence: DeviceLinkTransportEvidence,
    ): Boolean
    fun verifyMessageSignature(peer: DeviceLinkPeer, message: DeviceLinkMessage): Boolean
    fun authorizeMessage(peer: DeviceLinkPeer, message: DeviceLinkMessage): Boolean
}

internal class DenyAllDeviceLinkSecurityPolicy : DeviceLinkSecurityPolicy {
    override fun verifyPeerIdentity(peer: DeviceLinkPeer, localAppArea: String) = false
    override fun verifyPeerConsent(peer: DeviceLinkPeer, localAppArea: String) = false
    override fun verifyTransportEvidence(
        peer: DeviceLinkPeer,
        evidence: DeviceLinkTransportEvidence,
    ) = false
    override fun verifyMessageSignature(peer: DeviceLinkPeer, message: DeviceLinkMessage) = false
    override fun authorizeMessage(peer: DeviceLinkPeer, message: DeviceLinkMessage) = false
}

internal class DeviceLinkConnectionManager(
    private val localAppArea: String,
    private val peerAppArea: String,
    private val ble: DeviceLinkBleTransport,
    private val securityPolicy: DeviceLinkSecurityPolicy,
    private val nowEpochSeconds: () -> Long = { System.currentTimeMillis() / 1_000 },
) {
    @Volatile
    var state: DeviceLinkState = DeviceLinkState.IDLE
        private set

    private var peer: DeviceLinkPeer? = null
    private var lastSequence = 0L
    private val closedSessionIds = linkedSetOf<String>()
    private val seenMessageIds = linkedSetOf<String>()
    private val seenNonces = linkedSetOf<String>()

    init {
        require(
            (localAppArea == "niknolig" && peerAppArea == "niknolig-defense") ||
                (localAppArea == "niknolig-defense" && peerAppArea == "niknolig"),
        )
    }

    @Synchronized
    fun connect(candidate: DeviceLinkPeer, localConsentConfirmed: Boolean): Boolean {
        if (state !in setOf(DeviceLinkState.IDLE, DeviceLinkState.REVOKED, DeviceLinkState.FAILED)) {
            return false
        }
        if (!localConsentConfirmed ||
            !isUuid(candidate.installationId) ||
            !isUuid(candidate.sessionId) ||
            candidate.appArea != peerAppArea ||
            candidate.sessionId in closedSessionIds ||
            closedSessionIds.size >= MAX_CLOSED_SESSIONS
        ) {
            return false
        }

        val trusted = try {
            securityPolicy.verifyPeerIdentity(candidate, localAppArea) &&
                securityPolicy.verifyPeerConsent(candidate, localAppArea)
        } catch (_: Exception) {
            false
        }
        if (!trusted) {
            state = DeviceLinkState.FAILED
            return false
        }

        peer = candidate
        lastSequence = 0
        seenMessageIds.clear()
        seenNonces.clear()
        state = DeviceLinkState.CONNECTING
        return try {
            ble.connect(candidate) { connected ->
                onConnectionResult(candidate.sessionId, connected)
            }
            true
        } catch (_: Exception) {
            failClosed()
            false
        }
    }

    @Synchronized
    fun receive(message: DeviceLinkMessage): Boolean {
        val activePeer = peer
        if (state != DeviceLinkState.CONNECTED || activePeer == null) return false
        val immutableMessage = message.copy(signature = message.signature.copyOf())
        if (!isValidEnvelope(activePeer, immutableMessage)) {
            failClosed()
            return false
        }

        val authenticatedAndAuthorized = try {
            securityPolicy.verifyMessageSignature(activePeer, immutableMessage) &&
                securityPolicy.authorizeMessage(activePeer, immutableMessage)
        } catch (_: Exception) {
            false
        }
        if (!authenticatedAndAuthorized) {
            failClosed()
            return false
        }

        lastSequence = immutableMessage.sequence
        seenMessageIds.add(immutableMessage.messageId)
        seenNonces.add(immutableMessage.nonce)
        if (immutableMessage.eventType == "session.revoke") {
            closedSessionIds.add(activePeer.sessionId)
            peer = null
            lastSequence = 0
            seenMessageIds.clear()
            seenNonces.clear()
            state = DeviceLinkState.REVOKED
            safeDisconnect()
        }
        return true
    }

    @Synchronized
    fun disconnect() {
        if (state != DeviceLinkState.REVOKED) state = DeviceLinkState.IDLE
        peer?.sessionId?.let(closedSessionIds::add)
        peer = null
        lastSequence = 0
        seenMessageIds.clear()
        seenNonces.clear()
        safeDisconnect()
    }

    @Synchronized
    fun revoke() {
        peer?.sessionId?.let(closedSessionIds::add)
        peer = null
        lastSequence = 0
        seenMessageIds.clear()
        seenNonces.clear()
        state = DeviceLinkState.REVOKED
        safeDisconnect()
    }

    @Synchronized
    private fun onConnectionResult(
        sessionId: String,
        evidence: DeviceLinkTransportEvidence?,
    ) {
        if (state != DeviceLinkState.CONNECTING || peer?.sessionId != sessionId) return
        val activePeer = peer ?: return failClosed()
        if (evidence == null ||
            evidence.sessionId != activePeer.sessionId ||
            evidence.peerInstallationId != activePeer.installationId ||
            !evidence.encrypted ||
            !evidence.mitmProtected
        ) {
            return failClosed()
        }
        val verified = try {
            securityPolicy.verifyTransportEvidence(activePeer, evidence)
        } catch (_: Exception) {
            false
        }
        if (!verified) return failClosed()
        state = DeviceLinkState.CONNECTED
    }

    private fun isValidEnvelope(
        activePeer: DeviceLinkPeer,
        message: DeviceLinkMessage,
    ): Boolean {
        val now = try {
            nowEpochSeconds()
        } catch (_: Exception) {
            return false
        }
        return message.contractVersion == "1.0" &&
            isUuid(message.messageId) &&
            message.sessionId == activePeer.sessionId &&
            message.senderInstallationId == activePeer.installationId &&
            message.senderAppArea == peerAppArea &&
            message.recipientAppArea == localAppArea &&
            message.sequence > lastSequence &&
            message.sequence <= MAX_SAFE_INTEGER &&
            message.messageId !in seenMessageIds &&
            message.nonce !in seenNonces &&
            seenMessageIds.size < MAX_MESSAGES_PER_SESSION &&
            seenNonces.size < MAX_MESSAGES_PER_SESSION &&
            message.eventType in ALLOWED_EVENTS &&
            message.issuedAtEpochSeconds in (now - MAX_CLOCK_SKEW_SECONDS)..(now + MAX_CLOCK_SKEW_SECONDS) &&
            message.expiresAtEpochSeconds > now &&
            message.expiresAtEpochSeconds > message.issuedAtEpochSeconds &&
            message.expiresAtEpochSeconds - message.issuedAtEpochSeconds <= MAX_MESSAGE_LIFETIME_SECONDS &&
            message.nonce.matches(NONCE_PATTERN) &&
            message.signature.size in MIN_SIGNATURE_BYTES..MAX_SIGNATURE_BYTES
    }

    private fun failClosed() {
        peer?.sessionId?.let(closedSessionIds::add)
        peer = null
        lastSequence = 0
        seenMessageIds.clear()
        seenNonces.clear()
        state = DeviceLinkState.FAILED
        safeDisconnect()
    }

    private fun safeDisconnect() {
        try {
            ble.disconnect()
        } catch (_: Exception) {
            state = DeviceLinkState.FAILED
        }
    }

    private fun isUuid(value: String): Boolean = UUID_PATTERN.matches(value)

    private companion object {
        val UUID_PATTERN = Regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
        val NONCE_PATTERN = Regex("^[A-Za-z0-9_-]{22,86}$")
        val ALLOWED_EVENTS = setOf("consent.accepted", "session.heartbeat", "session.revoke")
        const val MAX_CLOCK_SKEW_SECONDS = 30
        const val MAX_MESSAGE_LIFETIME_SECONDS = 120
        const val MIN_SIGNATURE_BYTES = 32
        const val MAX_SIGNATURE_BYTES = 512
        const val MAX_SAFE_INTEGER = 9_007_199_254_740_991L
        const val MAX_MESSAGES_PER_SESSION = 1_024
        const val MAX_CLOSED_SESSIONS = 128
    }
}

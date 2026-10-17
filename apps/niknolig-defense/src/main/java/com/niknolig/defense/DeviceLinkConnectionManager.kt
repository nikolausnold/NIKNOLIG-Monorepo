package com.niknolig.defense

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

internal interface DeviceLinkBleTransport {
    fun connect(peer: DeviceLinkPeer, onResult: (Boolean) -> Unit)
    fun disconnect()
}

internal interface DeviceLinkSecurityPolicy {
    fun verifyPeerIdentity(peer: DeviceLinkPeer, localAppArea: String): Boolean
    fun verifyPeerConsent(peer: DeviceLinkPeer, localAppArea: String): Boolean
    fun verifyMessageSignature(peer: DeviceLinkPeer, message: DeviceLinkMessage): Boolean
    fun authorizeMessage(peer: DeviceLinkPeer, message: DeviceLinkMessage): Boolean
}

internal class DenyAllDeviceLinkSecurityPolicy : DeviceLinkSecurityPolicy {
    override fun verifyPeerIdentity(peer: DeviceLinkPeer, localAppArea: String) = false
    override fun verifyPeerConsent(peer: DeviceLinkPeer, localAppArea: String) = false
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
    var state: DeviceLinkState = DeviceLinkState.IDLE
        private set

    private var peer: DeviceLinkPeer? = null
    private var lastSequence = 0L
    private val revokedSessionIds = linkedSetOf<String>()

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
            candidate.sessionId in revokedSessionIds ||
            revokedSessionIds.size >= MAX_REVOKED_SESSIONS
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
        if (!isValidEnvelope(activePeer, message)) {
            failClosed()
            return false
        }

        val authenticatedAndAuthorized = try {
            securityPolicy.verifyMessageSignature(activePeer, message) &&
                securityPolicy.authorizeMessage(activePeer, message)
        } catch (_: Exception) {
            false
        }
        if (!authenticatedAndAuthorized) {
            failClosed()
            return false
        }

        lastSequence = message.sequence
        if (message.eventType == "session.revoke") {
            revokedSessionIds.add(activePeer.sessionId)
            peer = null
            state = DeviceLinkState.REVOKED
            safeDisconnect()
        }
        return true
    }

    @Synchronized
    fun disconnect() {
        if (state != DeviceLinkState.REVOKED) state = DeviceLinkState.IDLE
        peer = null
        lastSequence = 0
        safeDisconnect()
    }

    @Synchronized
    fun revoke() {
        peer?.sessionId?.let(revokedSessionIds::add)
        peer = null
        lastSequence = 0
        state = DeviceLinkState.REVOKED
        safeDisconnect()
    }

    @Synchronized
    private fun onConnectionResult(sessionId: String, connected: Boolean) {
        if (state != DeviceLinkState.CONNECTING || peer?.sessionId != sessionId) return
        if (!connected) return failClosed()
        state = DeviceLinkState.CONNECTED
    }

    private fun isValidEnvelope(
        activePeer: DeviceLinkPeer,
        message: DeviceLinkMessage,
    ): Boolean {
        val now = nowEpochSeconds()
        return message.contractVersion == "1.0" &&
            isUuid(message.messageId) &&
            message.sessionId == activePeer.sessionId &&
            message.senderInstallationId == activePeer.installationId &&
            message.senderAppArea == peerAppArea &&
            message.recipientAppArea == localAppArea &&
            message.sequence > lastSequence &&
            message.eventType in ALLOWED_EVENTS &&
            message.issuedAtEpochSeconds in (now - MAX_CLOCK_SKEW_SECONDS)..(now + MAX_CLOCK_SKEW_SECONDS) &&
            message.expiresAtEpochSeconds > now &&
            message.expiresAtEpochSeconds > message.issuedAtEpochSeconds &&
            message.expiresAtEpochSeconds - message.issuedAtEpochSeconds <= MAX_MESSAGE_LIFETIME_SECONDS &&
            message.nonce.matches(NONCE_PATTERN) &&
            message.signature.size in MIN_SIGNATURE_BYTES..MAX_SIGNATURE_BYTES
    }

    private fun failClosed() {
        peer = null
        lastSequence = 0
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
        const val MAX_REVOKED_SESSIONS = 128
    }
}

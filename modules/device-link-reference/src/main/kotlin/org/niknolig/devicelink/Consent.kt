package org.niknolig.devicelink

/**
 * Placeholder data scopes used to exercise the authorization model. They are NOT an
 * approved allowlist; the real list needs product/privacy approval (design doc §2).
 */
enum class DataScope { STATUS_SUMMARY, ALERT_NOTIFICATION, SENSOR_SUMMARY }

/** Direction relative to the local device. */
enum class Direction { SEND, RECEIVE }

/** Which app may do what with which scope. The shipped default allows nothing. */
class RolePolicy(private val allowed: Set<Triple<AppScope, DataScope, Direction>>) {
    fun permits(local: AppScope, scope: DataScope, direction: Direction) =
        Triple(local, scope, direction) in allowed

    companion object {
        val DENY_ALL = RolePolicy(emptySet())
    }
}

class PairedPeer(val id: DeviceId, val scope: AppScope, internal val publicKey: ByteArray)

enum class PeerState { TRUSTED, REVOKED }

sealed class Decision {
    data object Allow : Decision()
    data class Deny(val reason: AuditResult) : Decision()
}

private data class Grant(val scope: DataScope, val direction: Direction, val expiresAt: Long)

/**
 * Trust registry. Pairing alone grants nothing: every data scope and direction needs
 * its own explicit, expiring user consent, and every decision defaults to deny.
 */
class PeerRegistry(
    private val local: AppScope,
    private val policy: RolePolicy,
    private val clock: Clock,
    private val audit: AuditSink,
    private val consentTtlMillis: Long = 24L * 60 * 60 * 1000,
) {
    private class Entry(val peer: PairedPeer, var state: PeerState) {
        val grants = mutableListOf<Grant>()
        var revocationNoticePending = false
        var revokedAtSequence = 0L
    }

    private val peers = mutableMapOf<DeviceId, Entry>()

    /**
     * Completes pairing only after the local user compared the confirmation code. A pairing result is
     * single-use, and a result whose handshake started before the peer's revocation can never restore
     * trust: only a handshake started after the revocation may.
     */
    @Synchronized
    fun completePairing(pending: PendingPairing, userConfirmed: Boolean): PairedPeer? {
        if (!pending.consume()) {
            audit.record(AuditType.PAIRING_FAILED, pending.peerId, AuditResult.REPLAY)
            return null
        }
        val existing = peers[pending.peerId]
        if (existing != null && existing.state == PeerState.REVOKED && pending.startSequence <= existing.revokedAtSequence) {
            audit.record(AuditType.PAIRING_FAILED, pending.peerId, AuditResult.PEER_REVOKED)
            return null
        }
        if (!userConfirmed) {
            audit.record(AuditType.PAIRING_FAILED, pending.peerId, AuditResult.USER_DECLINED)
            return null
        }
        val peer = PairedPeer(pending.peerId, pending.peerScope, pending.peerPublicKey)
        peers[peer.id] = Entry(peer, PeerState.TRUSTED) // a fresh pairing replaces a revoked entry
        audit.record(AuditType.PAIRING_COMPLETED, peer.id, AuditResult.OK)
        return peer
    }

    fun state(id: DeviceId): PeerState? = peers[id]?.state

    fun trustedKey(id: DeviceId): ByteArray? = peers[id]?.takeIf { it.state == PeerState.TRUSTED }?.peer?.publicKey

    fun grant(id: DeviceId, scope: DataScope, direction: Direction, userConfirmed: Boolean): Boolean {
        val entry = peers[id]?.takeIf { it.state == PeerState.TRUSTED }
        if (entry == null || !userConfirmed || !policy.permits(local, scope, direction)) {
            audit.record(AuditType.AUTHORIZATION_DENIED, id, if (entry == null) AuditResult.UNKNOWN_PEER else AuditResult.NO_CONSENT)
            return false
        }
        entry.grants.removeAll { it.scope == scope && it.direction == direction }
        entry.grants += Grant(scope, direction, clock.nowMillis() + consentTtlMillis)
        audit.record(AuditType.CONSENT_GRANTED, id, AuditResult.OK)
        return true
    }

    fun revokeConsent(id: DeviceId, scope: DataScope, direction: Direction) {
        val entry = peers[id] ?: return
        entry.grants.removeAll { it.scope == scope && it.direction == direction }
        audit.record(AuditType.CONSENT_REVOKED, id, AuditResult.OK)
    }

    /**
     * Revocation takes effect locally at once, also while the peer is offline. The peer is
     * informed on the next authenticated contact; until then the pending flag stays set.
     * A revoked peer can only return through a completely new, user-confirmed pairing.
     */
    @Synchronized
    fun revokePeer(id: DeviceId) {
        val entry = peers[id] ?: return
        entry.state = PeerState.REVOKED
        entry.revokedAtSequence = PairingSequence.next()
        entry.grants.clear()
        entry.revocationNoticePending = true
        audit.record(AuditType.PEER_REVOKED, id, AuditResult.OK)
    }

    fun pendingRevocationNotices(): List<DeviceId> =
        peers.values.filter { it.revocationNoticePending }.map { it.peer.id }

    fun noticeDelivered(id: DeviceId) { peers[id]?.revocationNoticePending = false }

    fun authorize(id: DeviceId, scope: DataScope, direction: Direction): Decision {
        val entry = peers[id]
        val decision = when {
            entry == null -> Decision.Deny(AuditResult.UNKNOWN_PEER)
            entry.state == PeerState.REVOKED -> Decision.Deny(AuditResult.PEER_REVOKED)
            !policy.permits(local, scope, direction) -> Decision.Deny(AuditResult.WRONG_DIRECTION)
            else -> {
                val grant = entry.grants.firstOrNull { it.scope == scope && it.direction == direction }
                when {
                    grant == null -> Decision.Deny(AuditResult.NO_CONSENT)
                    clock.nowMillis() > grant.expiresAt -> Decision.Deny(AuditResult.CONSENT_EXPIRED)
                    else -> Decision.Allow
                }
            }
        }
        if (decision is Decision.Deny) audit.record(AuditType.AUTHORIZATION_DENIED, id, decision.reason)
        return decision
    }
}

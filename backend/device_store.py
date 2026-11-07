"""PostgreSQL persistence and state transitions for the device connection API.

Every public method is one transaction. Expiry uses the database clock. No method
returns or logs key material, tokens or pairing codes.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import psycopg
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row

import device_security as sec

SCOPES = ("status:read", "events:read", "alerts:send")
MAX_GRANT_SECONDS = 7 * 24 * 3600
MAX_PAGE = 100


class Conflict(Exception):
    pass


class NotFound(Exception):
    pass


class Forbidden(Exception):
    pass


def _device_view(row, prefix=""):
    return {
        "id": str(row[prefix + "id"]),
        "appArea": row[prefix + "app_area"],
        "displayName": row[prefix + "display_name"],
        "fingerprint": row[prefix + "public_key_fingerprint"],
        "state": row[prefix + "identity_state"],
    }


class DeviceStore:
    def __init__(self, connect, secret: bytes):
        self._connect = connect
        self._secret = secret

    def _tx(self):
        connection = self._connect()
        connection.row_factory = dict_row
        return connection

    @staticmethod
    def _event(cur, device_id, kind, *, source=None, link_id=None, detail=None):
        cur.execute(
            "INSERT INTO device_events(device_id, source_device_id, link_id, kind, detail) "
            "VALUES (%s, %s, %s, %s, %s)",
            (device_id, source, link_id, kind, detail),
        )

    # ---- identity -------------------------------------------------------
    def register_device(self, *, area, principal, installation_id, public_key, display_name):
        fp = sec.fingerprint(public_key)
        with self._tx() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM device_installations "
                "WHERE app_area = %s AND installation_reference = %s FOR UPDATE",
                (area, installation_id),
            )
            row = cur.fetchone()
            if row:
                if (row["principal_reference"] != principal
                        or row["identity_state"] != "verified"
                        or bytes(row["public_key"] or b"") != public_key):
                    raise Conflict
                return _device_view(row)
            try:
                cur.execute(
                    "INSERT INTO device_installations(id, app_area, principal_reference, "
                    "installation_reference, public_key, public_key_fingerprint, "
                    "identity_state, verified_at, display_name) "
                    "VALUES (%s, %s, %s, %s, %s, %s, 'verified', now(), %s) RETURNING *",
                    (uuid4(), area, principal, installation_id, public_key, fp, display_name),
                )
            except UniqueViolation:
                raise Conflict from None
            row = cur.fetchone()
            self._event(cur, row["id"], "device_registered")
            return _device_view(row)

    def get_device(self, device_id):
        with self._tx() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM device_installations WHERE id = %s", (device_id,))
            return cur.fetchone()

    def revoke_device(self, device_id, *, principal=None):
        with self._tx() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM device_installations WHERE id = %s FOR UPDATE", (device_id,))
            row = cur.fetchone()
            if not row or (principal is not None and row["principal_reference"] != principal):
                raise NotFound
            if row["identity_state"] == "revoked":
                return
            cur.execute(
                "UPDATE device_installations SET identity_state = 'revoked', revoked_at = now() "
                "WHERE id = %s", (device_id,))
            cur.execute(
                "UPDATE device_sessions SET revoked_at = now(), revoke_reason = 'device_revoked' "
                "WHERE device_id = %s AND revoked_at IS NULL", (device_id,))
            cur.execute(
                "UPDATE device_pairings SET state = 'cancelled' WHERE state IN ('open', 'claimed') "
                "AND (initiator_device_id = %s OR claimant_device_id = %s)", (device_id, device_id))
            cur.execute(
                "SELECT id, first_device_id, second_device_id FROM device_links "
                "WHERE state IN ('pending', 'active') AND (first_device_id = %s OR second_device_id = %s) "
                "FOR UPDATE", (device_id, device_id))
            for link in cur.fetchall():
                self._revoke_link_rows(cur, link["id"])
                peer = link["second_device_id"] if link["first_device_id"] == device_id else link["first_device_id"]
                self._event(cur, peer, "link_revoked", link_id=link["id"], detail="peer device revoked")
            self._event(cur, device_id, "device_revoked")

    # ---- sessions -------------------------------------------------------
    def create_challenge(self, device_id):
        nonce = sec.new_secret_token()
        with self._tx() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO device_challenges(nonce_hash, device_id, expires_at) "
                "SELECT %s, id, now() + make_interval(secs => %s) FROM device_installations "
                "WHERE id = %s AND identity_state = 'verified'",
                (sec.hash_token(nonce), sec.CHALLENGE_TTL_SECONDS, device_id),
            )
        return nonce

    def open_session(self, device_id, nonce, signature):
        """Consume the challenge exactly once, then verify the device signature."""
        with self._tx() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE device_challenges SET used_at = now() WHERE nonce_hash = %s "
                "AND device_id = %s AND used_at IS NULL AND expires_at > now() RETURNING 1",
                (sec.hash_token(nonce), device_id),
            )
            if not cur.fetchone():
                return None
            cur.execute(
                "SELECT * FROM device_installations WHERE id = %s AND identity_state = 'verified'",
                (device_id,))
            device = cur.fetchone()
            if not device or not sec.verify_signature(
                    bytes(device["public_key"]), signature,
                    sec.session_message(str(device_id), nonce)):
                return None
            session_id, refresh = uuid4(), sec.new_secret_token()
            cur.execute(
                "INSERT INTO device_sessions(id, device_id, refresh_hash, expires_at) "
                "VALUES (%s, %s, %s, now() + make_interval(secs => %s))",
                (session_id, device_id, sec.hash_token(refresh), sec.REFRESH_TOKEN_TTL_SECONDS))
            self._event(cur, device_id, "session_created")
            return self._tokens(device, session_id, refresh)

    def _tokens(self, device, session_id, refresh):
        access, expires = sec.issue_access_token(
            self._secret, device_id=device["id"], session_id=session_id, area=device["app_area"])
        return {"accessToken": access, "accessTokenExpiresAt": expires, "refreshToken": refresh,
                "refreshTokenExpiresInSeconds": sec.REFRESH_TOKEN_TTL_SECONDS,
                "deviceId": str(device["id"])}

    def refresh_session(self, refresh_token):
        digest = sec.hash_token(refresh_token)
        with self._tx() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT s.id AS session_id, s.revoked_at AS session_revoked_at, s.expires_at > now() AS live, d.* FROM device_sessions s "
                "JOIN device_installations d ON d.id = s.device_id "
                "WHERE s.refresh_hash = %s FOR UPDATE OF s", (digest,))
            row = cur.fetchone()
            if row:
                if row["session_revoked_at"] is not None or not row["live"] or row["identity_state"] != "verified":
                    return None
                refresh = sec.new_secret_token()
                cur.execute(
                    "UPDATE device_sessions SET refresh_hash = %s, previous_refresh_hash = %s, "
                    "rotated_at = now() WHERE id = %s",
                    (sec.hash_token(refresh), digest, row["session_id"]))
                return self._tokens(row, row["session_id"], refresh)
            cur.execute(
                "UPDATE device_sessions SET revoked_at = now(), revoke_reason = 'refresh_reuse' "
                "WHERE previous_refresh_hash = %s AND revoked_at IS NULL RETURNING device_id", (digest,))
            reused = cur.fetchone()
            if reused:
                self._event(cur, reused["device_id"], "session_refresh_reuse_detected",
                            detail="session revoked")
            return None

    def authenticate_access(self, claims):
        with self._tx() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT d.* FROM device_sessions s JOIN device_installations d ON d.id = s.device_id "
                "WHERE s.id = %s AND s.device_id = %s AND s.revoked_at IS NULL "
                "AND s.expires_at > now() AND d.identity_state = 'verified' AND d.app_area = %s",
                (claims["sid"], claims["sub"], claims["area"]))
            row = cur.fetchone()
            return dict(row, session_id=UUID(claims["sid"])) if row else None

    def revoke_session(self, session_id, device_id):
        with self._tx() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE device_sessions SET revoked_at = now(), revoke_reason = 'device_logout' "
                "WHERE id = %s AND device_id = %s AND revoked_at IS NULL", (session_id, device_id))
            self._event(cur, device_id, "session_revoked")

    def list_sessions(self, device_id):
        with self._tx() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id, created_at, expires_at FROM device_sessions WHERE device_id = %s "
                "AND revoked_at IS NULL AND expires_at > now() ORDER BY created_at DESC", (device_id,))
            return [{"id": str(r["id"]), "createdAt": r["created_at"].isoformat(),
                     "expiresAt": r["expires_at"].isoformat()} for r in cur.fetchall()]

    # ---- pairing --------------------------------------------------------
    def create_pairing(self, device):
        code = sec.new_pairing_code()
        pairing_id = uuid4()
        with self._tx() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE device_pairings SET state = 'cancelled' WHERE initiator_device_id = %s "
                "AND state IN ('open', 'claimed')", (device["id"],))
            cur.execute(
                "INSERT INTO device_pairings(id, initiator_device_id, code_hash, expires_at) "
                "VALUES (%s, %s, %s, now() + make_interval(secs => %s)) RETURNING expires_at",
                (pairing_id, device["id"], sec.pairing_code_hash(self._secret, code),
                 sec.PAIRING_OPEN_SECONDS))
            expires = cur.fetchone()["expires_at"]
            self._event(cur, device["id"], "pairing_created")
        return {"pairingId": str(pairing_id), "code": code, "expiresAt": expires.isoformat()}

    def claim_pairing(self, device, code):
        with self._tx() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT p.*, d.app_area AS initiator_area, d.public_key_fingerprint AS initiator_fp, "
                "d.identity_state AS initiator_state FROM device_pairings p "
                "JOIN device_installations d ON d.id = p.initiator_device_id "
                "WHERE p.code_hash = %s AND p.state = 'open' AND p.expires_at > now() FOR UPDATE OF p",
                (sec.pairing_code_hash(self._secret, code),))
            row = cur.fetchone()
            if (not row or row["initiator_device_id"] == device["id"]
                    or row["initiator_area"] == device["app_area"]
                    or row["initiator_state"] != "verified"):
                return None
            cur.execute(
                "SELECT 1 FROM device_links WHERE state IN ('pending', 'active') "
                "AND LEAST(first_device_id, second_device_id) = LEAST(%s::uuid, %s::uuid) "
                "AND GREATEST(first_device_id, second_device_id) = GREATEST(%s::uuid, %s::uuid)",
                (device["id"], row["initiator_device_id"], device["id"], row["initiator_device_id"]))
            if cur.fetchone():
                raise Conflict
            cur.execute(
                "UPDATE device_pairings SET state = 'claimed', claimant_device_id = %s, "
                "expires_at = now() + make_interval(secs => %s) WHERE id = %s",
                (device["id"], sec.PAIRING_CONFIRM_SECONDS, row["id"]))
            self._event(cur, row["initiator_device_id"], "pairing_claimed", source=device["id"])
            return self._pairing_view(cur, row["id"], device["id"])

    def get_pairing(self, pairing_id, device_id):
        with self._tx() as conn, conn.cursor() as cur:
            return self._pairing_view(cur, pairing_id, device_id)

    def _pairing_view(self, cur, pairing_id, device_id):
        cur.execute(
            "SELECT p.*, p.expires_at <= now() AS expired, "
            "i.id AS i_id, i.app_area AS i_app_area, i.display_name AS i_display_name, "
            "i.public_key_fingerprint AS i_public_key_fingerprint, i.identity_state AS i_identity_state, "
            "c.id AS c_id, c.app_area AS c_app_area, c.display_name AS c_display_name, "
            "c.public_key_fingerprint AS c_public_key_fingerprint, c.identity_state AS c_identity_state "
            "FROM device_pairings p JOIN device_installations i ON i.id = p.initiator_device_id "
            "LEFT JOIN device_installations c ON c.id = p.claimant_device_id WHERE p.id = %s",
            (pairing_id,))
        row = cur.fetchone()
        if not row or device_id not in (row["initiator_device_id"], row["claimant_device_id"]):
            raise NotFound
        state = row["state"]
        if state in ("open", "claimed") and row["expired"]:
            state = "expired"
        initiator = row["initiator_device_id"] == device_id
        peer = _device_view(row, "c_") if initiator and row["c_id"] else (
            None if initiator else _device_view(row, "i_"))
        view = {"pairingId": str(row["id"]), "state": state, "role": "initiator" if initiator else "claimant",
                "expiresAt": row["expires_at"].isoformat(), "peer": peer,
                "confirmedByMe": bool(row["initiator_confirmed_at" if initiator else "claimant_confirmed_at"]),
                "confirmedByPeer": bool(row["claimant_confirmed_at" if initiator else "initiator_confirmed_at"]),
                "linkId": str(row["link_id"]) if row["link_id"] else None}
        if state == "claimed":
            view["shortAuthString"] = sec.short_auth_string(
                str(row["id"]), row["i_public_key_fingerprint"], row["c_public_key_fingerprint"])
        return view

    def confirm_pairing(self, pairing_id, device_id):
        with self._tx() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM device_pairings WHERE id = %s FOR UPDATE", (pairing_id,))
            row = cur.fetchone()
            if not row or device_id not in (row["initiator_device_id"], row["claimant_device_id"]):
                raise NotFound
            cur.execute("SELECT now() < %s AS live", (row["expires_at"],))
            if row["state"] != "claimed" or not cur.fetchone()["live"]:
                raise Conflict
            column = "initiator_confirmed_at" if device_id == row["initiator_device_id"] else "claimant_confirmed_at"
            cur.execute(f"UPDATE device_pairings SET {column} = COALESCE({column}, now()) "
                        "WHERE id = %s RETURNING initiator_confirmed_at, claimant_confirmed_at", (pairing_id,))
            confirmed = cur.fetchone()
            if confirmed["initiator_confirmed_at"] and confirmed["claimant_confirmed_at"]:
                cur.execute("SELECT app_area FROM device_installations WHERE id = %s", (row["initiator_device_id"],))
                first_area = cur.fetchone()["app_area"]
                cur.execute("SELECT app_area FROM device_installations WHERE id = %s", (row["claimant_device_id"],))
                second_area = cur.fetchone()["app_area"]
                link_id = uuid4()
                try:
                    cur.execute(
                        "INSERT INTO device_links(id, first_device_id, first_app_area, second_device_id, "
                        "second_app_area, state, expires_at, activated_at) VALUES "
                        "(%s, %s, %s, %s, %s, 'active', now() + make_interval(secs => %s), now())",
                        (link_id, row["initiator_device_id"], first_area, row["claimant_device_id"],
                         second_area, sec.LINK_TTL_SECONDS))
                except UniqueViolation:
                    raise Conflict from None
                cur.execute("UPDATE device_pairings SET state = 'confirmed', link_id = %s WHERE id = %s",
                            (link_id, pairing_id))
                for mine, other in ((row["initiator_device_id"], row["claimant_device_id"]),
                                    (row["claimant_device_id"], row["initiator_device_id"])):
                    self._event(cur, mine, "link_activated", source=other, link_id=link_id)
            return self._pairing_view(cur, pairing_id, device_id)

    def cancel_pairing(self, pairing_id, device_id):
        with self._tx() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM device_pairings WHERE id = %s FOR UPDATE", (pairing_id,))
            row = cur.fetchone()
            if not row or device_id not in (row["initiator_device_id"], row["claimant_device_id"]):
                raise NotFound
            if row["state"] in ("open", "claimed"):
                cur.execute("UPDATE device_pairings SET state = 'cancelled' WHERE id = %s", (pairing_id,))
                self._event(cur, device_id, "pairing_cancelled")

    # ---- links ----------------------------------------------------------
    def list_links(self, device_id):
        with self._tx() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT l.id AS link_id, l.state, l.activated_at, l.expires_at, l.revoked_at, "
                "l.expires_at <= now() AS expired, p.* FROM device_links l "
                "JOIN device_installations p ON p.id = CASE WHEN l.first_device_id = %s "
                "THEN l.second_device_id ELSE l.first_device_id END "
                "WHERE (l.first_device_id = %s OR l.second_device_id = %s) AND l.state = 'active' "
                "ORDER BY l.created_at DESC", (device_id, device_id, device_id))
            return [{"linkId": str(r["link_id"]), "state": "expired" if r["expired"] else r["state"],
                     "activatedAt": r["activated_at"].isoformat(),
                     "expiresAt": r["expires_at"].isoformat(), "peer": _device_view(r)}
                    for r in cur.fetchall()]

    def _active_link(self, cur, link_id, device_id, lock=False):
        cur.execute(
            "SELECT * FROM device_links WHERE id = %s AND state = 'active' AND expires_at > now() "
            "AND (first_device_id = %s OR second_device_id = %s)" + (" FOR UPDATE" if lock else ""),
            (link_id, device_id, device_id))
        link = cur.fetchone()
        if not link:
            raise NotFound
        peer = link["second_device_id"] if link["first_device_id"] == device_id else link["first_device_id"]
        return link, peer

    def _revoke_link_rows(self, cur, link_id):
        cur.execute("UPDATE device_links SET state = 'revoked', revoked_at = now() WHERE id = %s", (link_id,))
        cur.execute("UPDATE device_grants SET revoked_at = now() WHERE link_id = %s AND revoked_at IS NULL",
                    (link_id,))

    def revoke_link(self, link_id, device_id):
        with self._tx() as conn, conn.cursor() as cur:
            _, peer = self._active_link(cur, link_id, device_id, lock=True)
            self._revoke_link_rows(cur, link_id)
            self._event(cur, device_id, "link_revoked", source=device_id, link_id=link_id)
            self._event(cur, peer, "link_revoked", source=device_id, link_id=link_id)

    # ---- grants ---------------------------------------------------------
    def create_grant(self, link_id, device_id, scope, ttl_seconds):
        with self._tx() as conn, conn.cursor() as cur:
            _, peer = self._active_link(cur, link_id, device_id, lock=True)
            grant_id = uuid4()
            cur.execute(
                "INSERT INTO device_grants(id, link_id, grantor_device_id, grantee_device_id, scope, expires_at) "
                "VALUES (%s, %s, %s, %s, %s, LEAST(now() + make_interval(secs => %s), "
                "(SELECT expires_at FROM device_links WHERE id = %s))) RETURNING expires_at",
                (grant_id, link_id, device_id, peer, scope, ttl_seconds, link_id))
            expires = cur.fetchone()["expires_at"]
            self._event(cur, device_id, "grant_created", source=device_id, link_id=link_id, detail=scope)
            self._event(cur, peer, "grant_received", source=device_id, link_id=link_id, detail=scope)
            return {"grantId": str(grant_id), "linkId": str(link_id), "scope": scope,
                    "direction": "given", "expiresAt": expires.isoformat()}

    def list_grants(self, link_id, device_id):
        with self._tx() as conn, conn.cursor() as cur:
            self._active_link(cur, link_id, device_id)
            cur.execute(
                "SELECT * FROM device_grants WHERE link_id = %s AND revoked_at IS NULL "
                "AND expires_at > now() ORDER BY created_at", (link_id,))
            return [{"grantId": str(r["id"]), "linkId": str(link_id), "scope": r["scope"],
                     "direction": "given" if r["grantor_device_id"] == device_id else "received",
                     "expiresAt": r["expires_at"].isoformat()} for r in cur.fetchall()]

    def revoke_grant(self, grant_id, device_id):
        with self._tx() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE device_grants SET revoked_at = now() WHERE id = %s AND grantor_device_id = %s "
                "AND revoked_at IS NULL RETURNING link_id, grantee_device_id, scope", (grant_id, device_id))
            row = cur.fetchone()
            if not row:
                raise NotFound
            self._event(cur, device_id, "grant_revoked", source=device_id, link_id=row["link_id"], detail=row["scope"])
            self._event(cur, row["grantee_device_id"], "grant_revoked", source=device_id,
                        link_id=row["link_id"], detail=row["scope"])

    def _require_grant(self, cur, link_id, requester_id, scope):
        """The *peer* must have granted `scope` to the requester on this link."""
        _, peer = self._active_link(cur, link_id, requester_id)
        cur.execute(
            "SELECT 1 FROM device_grants WHERE link_id = %s AND grantor_device_id = %s "
            "AND grantee_device_id = %s AND scope = %s AND revoked_at IS NULL AND expires_at > now()",
            (link_id, peer, requester_id, scope))
        if not cur.fetchone():
            raise Forbidden
        return peer

    # ---- status and events ---------------------------------------------
    def set_status(self, device_id, state, detail):
        with self._tx() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO device_status(device_id, state, detail) VALUES (%s, %s, %s) "
                "ON CONFLICT (device_id) DO UPDATE SET state = EXCLUDED.state, "
                "detail = EXCLUDED.detail, reported_at = now()", (device_id, state, detail))
            self._event(cur, device_id, "status_changed", detail=state)

    def _status_row(self, cur, device_id):
        cur.execute("SELECT state, detail, reported_at FROM device_status WHERE device_id = %s", (device_id,))
        row = cur.fetchone()
        if not row:
            return {"state": "unknown", "detail": None, "reportedAt": None}
        return {"state": row["state"], "detail": row["detail"], "reportedAt": row["reported_at"].isoformat()}

    def get_status(self, device_id):
        with self._tx() as conn, conn.cursor() as cur:
            return self._status_row(cur, device_id)

    def get_peer_status(self, link_id, device_id):
        with self._tx() as conn, conn.cursor() as cur:
            peer = self._require_grant(cur, link_id, device_id, "status:read")
            return self._status_row(cur, peer)

    def add_event(self, device_id, kind, detail):
        with self._tx() as conn, conn.cursor() as cur:
            self._event(cur, device_id, kind, source=device_id, detail=detail)

    def send_alert(self, link_id, device_id, kind, detail):
        with self._tx() as conn, conn.cursor() as cur:
            _, peer = self._active_link(cur, link_id, device_id)
            cur.execute(
                "SELECT 1 FROM device_grants WHERE link_id = %s AND grantor_device_id = %s "
                "AND grantee_device_id = %s AND scope = 'alerts:send' AND revoked_at IS NULL "
                "AND expires_at > now()", (link_id, peer, device_id))
            if not cur.fetchone():
                raise Forbidden
            self._event(cur, peer, kind, source=device_id, link_id=link_id, detail=detail)
            self._event(cur, device_id, "alert_sent", source=device_id, link_id=link_id, detail=kind)

    def _events(self, cur, device_id, after, limit):
        cur.execute(
            "SELECT id, kind, detail, link_id, source_device_id, created_at FROM device_events "
            "WHERE device_id = %s AND id < %s ORDER BY id DESC LIMIT %s", (device_id, after, limit))
        return [{"id": r["id"], "kind": r["kind"], "detail": r["detail"],
                 "linkId": str(r["link_id"]) if r["link_id"] else None,
                 "sourceDeviceId": str(r["source_device_id"]) if r["source_device_id"] else None,
                 "createdAt": r["created_at"].isoformat()} for r in cur.fetchall()]

    def list_events(self, device_id, after, limit):
        with self._tx() as conn, conn.cursor() as cur:
            return self._events(cur, device_id, after, min(limit, MAX_PAGE))

    def list_peer_events(self, link_id, device_id, after, limit):
        with self._tx() as conn, conn.cursor() as cur:
            peer = self._require_grant(cur, link_id, device_id, "events:read")
            return self._events(cur, peer, after, min(limit, MAX_PAGE))

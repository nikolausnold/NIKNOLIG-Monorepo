"""PostgreSQL authority for the opt-in local reference API.

Every operation opens a short transaction. Principal advisory locks precede
device row locks, including revoke, so registration and possession transitions
cannot race. The caller must supply an already authenticated principal.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timezone

import psycopg
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from psycopg.rows import dict_row


class StoreError(Exception):
    pass


class Unavailable(StoreError):
    pass


class Conflict(StoreError):
    pass


class NotFound(StoreError):
    pass


class Denied(StoreError):
    pass


class RateLimited(StoreError):
    pass


def digest(*parts):
    # Length-prefixing prevents delimiter ambiguity in issuer/jti and subjects.
    data = "".join(f"{len(p)}:{p}" for p in parts).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def timestamp(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z") if value else None


def device_json(row):
    return {
        "id": str(row["id"]),
        "installationId": str(row["installation_reference"]),
        "appArea": row["app_area"],
        "state": row["identity_state"],
        "createdAt": timestamp(row["created_at"]),
        "verifiedAt": timestamp(row["verified_at"]),
        "revokedAt": timestamp(row["revoked_at"]),
    }


class PostgresStore:
    def __init__(self, dsn, principal_limit=60, global_limit=6000):
        self.dsn = dsn
        self.principal_limit = principal_limit
        self.global_limit = global_limit

    def _connect(self):
        if not self.dsn:
            raise Unavailable()
        try:
            return psycopg.connect(
                self.dsn, connect_timeout=3, row_factory=dict_row,
                options="-c statement_timeout=5000 -c lock_timeout=3000",
            )
        except psycopg.Error:
            raise Unavailable() from None

    def _run(self, operation):
        try:
            with self._connect() as conn:
                return operation(conn)
        except psycopg.errors.UniqueViolation:
            raise Conflict() from None
        except psycopg.Error:
            raise Unavailable() from None

    @staticmethod
    def _principal_lock(conn, area, principal):
        conn.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
            (digest("principal", area, principal),),
        )

    def ready(self):
        def operation(conn):
            conn.execute("SELECT 1").fetchone()
            found = conn.execute(
                "SELECT version FROM backend_schema_migrations WHERE version = %s",
                ("002_backend_api",),
            ).fetchone()
            # Exercise required schema, not just a marker that could be stale.
            conn.execute("SELECT public_key FROM device_installations LIMIT 0")
            conn.execute("SELECT token_hash FROM backend_token_revocations LIMIT 0")
            conn.execute("SELECT bucket_key FROM backend_rate_limits LIMIT 0")
            conn.execute("SELECT message FROM backend_device_challenges LIMIT 0")
            return bool(found)
        return self._run(operation)

    def authorize(self, token_hash, area, principal):
        def operation(conn):
            # At most 100 expired rows per table/request; scheduled maintenance
            # may delete remaining expired rows during sustained high traffic.
            conn.execute(
                "DELETE FROM backend_token_revocations WHERE token_hash IN "
                "(SELECT token_hash FROM backend_token_revocations "
                "WHERE expires_at <= now() ORDER BY expires_at LIMIT 100)"
            )
            conn.execute(
                "DELETE FROM backend_device_challenges WHERE id IN "
                "(SELECT id FROM backend_device_challenges "
                "WHERE expires_at <= now() ORDER BY expires_at LIMIT 100)"
            )
            conn.execute(
                "DELETE FROM backend_rate_limits WHERE (bucket_key, window_start) IN "
                "(SELECT bucket_key, window_start FROM backend_rate_limits "
                "WHERE window_start < floor(extract(epoch FROM now()) / 60)::bigint "
                "ORDER BY window_start LIMIT 100)"
            )
            if conn.execute(
                "SELECT 1 FROM backend_token_revocations "
                "WHERE token_hash = %s AND expires_at > now()", (token_hash,),
            ).fetchone():
                return "revoked"
            # Fixed order and fixed-width global key avoid deadlocks/cardinality
            # growth from jti. Increment-and-check commits even denied requests.
            exceeded = False
            for key, limit in (
                (digest("global"), self.global_limit),
                (digest("principal-rate", area, principal), self.principal_limit),
            ):
                row = conn.execute(
                    "INSERT INTO backend_rate_limits (bucket_key, window_start, requests) "
                    "VALUES (%s, floor(extract(epoch FROM now()) / 60)::bigint, 1) "
                    "ON CONFLICT (bucket_key, window_start) DO UPDATE "
                    "SET requests = LEAST(backend_rate_limits.requests + 1, 2147483647) "
                    "RETURNING requests", (key,),
                ).fetchone()
                exceeded |= row["requests"] > limit
            return "rate" if exceeded else "ok"
        result = self._run(operation)
        if result == "revoked":
            raise Denied()
        if result == "rate":
            raise RateLimited()

    def logout(self, token_hash, expires):
        self._run(lambda conn: conn.execute(
            "INSERT INTO backend_token_revocations (token_hash, expires_at) "
            "VALUES (%s, %s) ON CONFLICT (token_hash) DO UPDATE "
            "SET expires_at = GREATEST(backend_token_revocations.expires_at, EXCLUDED.expires_at)",
            (token_hash, datetime.fromtimestamp(expires, timezone.utc)),
        ))

    def list_devices(self, area, principal):
        return self._run(lambda conn: [
            device_json(row) for row in conn.execute(
                "SELECT * FROM device_installations WHERE app_area = %s "
                "AND principal_reference = %s ORDER BY created_at, id LIMIT 100",
                (area, principal),
            ).fetchall()
        ])

    @staticmethod
    def _device(conn, area, principal, device_id):
        row = conn.execute(
            "SELECT * FROM device_installations WHERE id = %s AND app_area = %s "
            "AND principal_reference = %s FOR UPDATE",
            (device_id, area, principal),
        ).fetchone()
        if not row:
            raise NotFound()
        return row

    def register(self, area, principal, installation_id, public_key, fingerprint):
        def operation(conn):
            self._principal_lock(conn, area, principal)
            count = conn.execute(
                "SELECT count(*) AS count FROM device_installations WHERE app_area = %s "
                "AND principal_reference = %s AND identity_state = 'pending'",
                (area, principal),
            ).fetchone()["count"]
            if count >= 100:
                raise Conflict()
            row = conn.execute(
                "INSERT INTO device_installations "
                "(id, app_area, principal_reference, installation_reference, public_key, public_key_fingerprint) "
                "VALUES (%s, %s, %s, %s, %s, %s) RETURNING *",
                (uuid.uuid4(), area, principal, installation_id, public_key, fingerprint),
            ).fetchone()
            return device_json(row)
        return self._run(operation)

    def get_device(self, area, principal, device_id):
        return self._run(lambda conn: device_json(self._device(conn, area, principal, device_id)))

    def revoke(self, area, principal, device_id):
        def operation(conn):
            self._principal_lock(conn, area, principal)
            self._device(conn, area, principal, device_id)
            row = conn.execute(
                "UPDATE device_installations SET identity_state = 'revoked', "
                "revoked_at = COALESCE(revoked_at, now()) WHERE id = %s RETURNING *",
                (device_id,),
            ).fetchone()
            conn.execute(
                "UPDATE backend_device_challenges SET consumed_at = COALESCE(consumed_at, now()) "
                "WHERE device_id = %s AND consumed_at IS NULL", (device_id,),
            )
            return device_json(row)
        return self._run(operation)

    def challenge(self, area, principal, device_id):
        def operation(conn):
            self._principal_lock(conn, area, principal)
            row = self._device(conn, area, principal, device_id)
            if row["identity_state"] == "revoked" or not row["public_key"]:
                raise Denied()
            # Only one challenge is retained per device. Replacement makes old
            # identifiers indistinguishable from replayed/invalid identifiers.
            conn.execute("DELETE FROM backend_device_challenges WHERE device_id = %s", (device_id,))
            challenge_id = uuid.uuid4()
            message = "\n".join((
                "NIKNOLIG-DEVICE-POSSESSION", "v1", area, str(device_id),
                str(challenge_id), secrets.token_urlsafe(32),
            ))
            challenge = conn.execute(
                "INSERT INTO backend_device_challenges "
                "(id, device_id, app_area, principal_reference, key_fingerprint, message, expires_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, now() + interval '120 seconds') "
                "RETURNING expires_at",
                (challenge_id, device_id, area, principal, row["public_key_fingerprint"], message),
            ).fetchone()
            return {"challengeId": str(challenge_id), "message": message,
                    "expiresAt": timestamp(challenge["expires_at"])}
        return self._run(operation)

    def verify(self, area, principal, device_id, challenge_id, signature):
        def operation(conn):
            self._principal_lock(conn, area, principal)
            device = self._device(conn, area, principal, device_id)
            challenge = conn.execute(
                "UPDATE backend_device_challenges SET consumed_at = now() "
                "WHERE id = %s AND device_id = %s AND app_area = %s "
                "AND principal_reference = %s AND consumed_at IS NULL "
                "RETURNING *, expires_at > now() AS unexpired",
                (challenge_id, device_id, area, principal),
            ).fetchone()
            # Returning rather than raising commits consumption on all failures.
            if (not challenge or not challenge["unexpired"]
                    or device["identity_state"] == "revoked"
                    or challenge["key_fingerprint"] != device["public_key_fingerprint"]):
                return None
            try:
                key = serialization.load_pem_public_key(device["public_key"].encode("ascii"))
                key.verify(signature, challenge["message"].encode("utf-8"), ec.ECDSA(hashes.SHA256()))
            except (InvalidSignature, ValueError, TypeError):
                return None
            row = conn.execute(
                "UPDATE device_installations SET identity_state = 'verified', "
                "verified_at = COALESCE(verified_at, now()) "
                "WHERE id = %s AND identity_state <> 'revoked' RETURNING *", (device_id,),
            ).fetchone()
            return device_json(row) if row else None
        result = self._run(operation)
        if result is None:
            raise Denied()
        return result

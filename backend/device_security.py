"""Cryptographic helpers for device identity, pairing and device-bound tokens.

Only vetted primitives are used (Ed25519, HMAC-SHA256, SHA-256, ``secrets``).
Nothing here logs or returns key material.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time
from collections import deque
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ACCESS_TOKEN_TTL_SECONDS = 300
REFRESH_TOKEN_TTL_SECONDS = 30 * 24 * 3600
CHALLENGE_TTL_SECONDS = 60
PAIRING_OPEN_SECONDS = 120
PAIRING_CONFIRM_SECONDS = 300
LINK_TTL_SECONDS = 365 * 24 * 3600
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"[:32]
CODE_LENGTH = 8
TOKEN_PREFIX = "v1"
MIN_SECRET_BYTES = 32


class TokenError(ValueError):
    pass


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(value: str, *, length: int | None = None) -> bytes:
    if not isinstance(value, str) or not value.isascii() or len(value) > 4096:
        raise ValueError("invalid base64url")
    try:
        data = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (binascii.Error, ValueError) as error:
        raise ValueError("invalid base64url") from error
    if b64url_encode(data) != value or (length is not None and len(data) != length):
        raise ValueError("invalid base64url")
    return data


def fingerprint(public_key: bytes) -> str:
    return hashlib.sha256(public_key).hexdigest()


def verify_signature(public_key: bytes, signature: bytes, message: bytes) -> bool:
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(signature, message)
    except (InvalidSignature, ValueError):
        return False
    return True


def registration_message(area: str, installation_id: str, principal: str) -> bytes:
    return "\n".join(
        ("niknolig-device-register-v1", area, installation_id, principal)
    ).encode()


def session_message(device_id: str, nonce: str) -> bytes:
    return "\n".join(("niknolig-device-session-v1", device_id, nonce)).encode()


def new_secret_token() -> str:
    return b64url_encode(secrets.token_bytes(32))


def hash_token(token: str) -> bytes:
    """SHA-256 is sufficient for 256-bit random tokens; they are never stored."""
    return hashlib.sha256(token.encode("ascii")).digest()


def new_pairing_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def normalize_pairing_code(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    code = value.replace("-", "").replace(" ", "").upper()
    if len(code) != CODE_LENGTH or any(ch not in CODE_ALPHABET for ch in code):
        return None
    return code


def pairing_code_hash(secret: bytes, code: str) -> bytes:
    return hmac.new(secret, b"pairing-code-v1|" + code.encode(), hashlib.sha256).digest()


def short_auth_string(pairing_id: str, first_fp: str, second_fp: str) -> str:
    digest = hashlib.sha256(
        f"niknolig-sas-v1|{pairing_id}|{first_fp}|{second_fp}".encode()
    ).digest()
    return f"{int.from_bytes(digest[:4], 'big') % 1_000_000:06d}"


def issue_access_token(
    secret: bytes, *, device_id: UUID, session_id: UUID, area: str, now: int | None = None
) -> tuple[str, int]:
    issued = int(time.time()) if now is None else now
    expires = issued + ACCESS_TOKEN_TTL_SECONDS
    body = b64url_encode(json.dumps(
        {"sub": str(device_id), "sid": str(session_id), "area": area,
         "iat": issued, "exp": expires},
        separators=(",", ":"), sort_keys=True,
    ).encode())
    signature = hmac.new(secret, f"{TOKEN_PREFIX}.{body}".encode(), hashlib.sha256).digest()
    return f"{TOKEN_PREFIX}.{body}.{b64url_encode(signature)}", expires


def verify_access_token(secret: bytes, token: str, *, now: int | None = None) -> dict:
    if not isinstance(token, str) or len(token) > 1024:
        raise TokenError
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != TOKEN_PREFIX:
        raise TokenError
    expected = hmac.new(secret, f"{parts[0]}.{parts[1]}".encode(), hashlib.sha256).digest()
    try:
        signature = b64url_decode(parts[2], length=32)
        claims = json.loads(b64url_decode(parts[1]))
        if not hmac.compare_digest(signature, expected):
            raise TokenError
        if not isinstance(claims, dict) or type(claims.get("exp")) is not int:
            raise TokenError
        UUID(claims["sub"]), UUID(claims["sid"])
    except (ValueError, KeyError, TypeError) as error:
        raise TokenError from error
    current = int(time.time()) if now is None else now
    if claims["exp"] <= current or claims.get("area") not in ("niknolig", "niknolig-defense"):
        raise TokenError
    return claims


def load_signing_secret(path: str) -> bytes:
    from pathlib import Path

    value = Path(path).read_text(encoding="utf-8").strip()
    try:
        secret = b64url_decode(value)
    except ValueError:
        secret = value.encode()
    if len(secret) < MIN_SECRET_BYTES:
        raise ValueError("Device token secret must contain at least 32 bytes")
    return secret


class SlidingWindowLimiter:
    """In-process limiter; per-instance state, bounded memory."""

    def __init__(self, limit: int, window_seconds: float, *, max_keys: int = 50_000, clock=time.monotonic):
        self.limit, self.window, self.max_keys, self.clock = limit, window_seconds, max_keys, clock
        self._hits: dict[str, deque] = {}

    def allow(self, key: str) -> bool:
        now = self.clock()
        hits = self._hits.get(key)
        if hits is None:
            if len(self._hits) >= self.max_keys:
                self._evict(now)
                if len(self._hits) >= self.max_keys:
                    return False
            hits = self._hits[key] = deque()
        while hits and now - hits[0] >= self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        return True

    def release(self, key: str):
        """Return the newest reservation (used when an attempt turned out legitimate)."""
        hits = self._hits.get(key)
        if hits:
            hits.pop()

    def exhausted(self, key: str) -> bool:
        hits = self._hits.get(key)
        if not hits:
            return False
        now = self.clock()
        while hits and now - hits[0] >= self.window:
            hits.popleft()
        return len(hits) >= self.limit

    def _evict(self, now):
        for key in [k for k, h in self._hits.items() if not h or now - h[-1] >= self.window]:
            del self._hits[key]

"""Fail-closed, consent-based long-term memory preparation.

Memories are explicit user-approved notes, not conversation logs, knowledge
entries or model training data. Every record is isolated by (app, subject).
The in-memory store is volatile and for tests/local preparation only; a
production adapter needs SecurityChain-P0 approval, encryption and a durable,
audited deletion path. Nothing here is wired to an HTTP route.
"""

from dataclasses import dataclass, replace
import math
import re
import threading
import time
from typing import Protocol
from uuid import UUID, uuid4

from ai_support import APPS, Principal


KINDS = frozenset({"preference", "fact"})
MAX_CONTENT_CHARS = 500
MAX_RECORDS_PER_PRINCIPAL = 100
MAX_RECALL = 5
DEFAULT_RETENTION_DAYS = 90
MAX_RETENTION_DAYS = 365
_CREDENTIAL_MARKER = re.compile(
    r"(?i)\b(password|passwd|secret|token|api[_-]?key|authorization)\b\s*[:=]\s*\S+"
)
_WORD = re.compile(r"[^\W_]+", re.UNICODE)


class MemoryEngineError(Exception):
    """Carries only a stable, non-sensitive reason code."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class MemoryRecord:
    id: UUID
    app: str
    subject: str
    kind: str
    content: str
    created_at: float
    updated_at: float
    expires_at: float


class MemoryStore(Protocol):
    def put(self, record: MemoryRecord, *, limit: int) -> bool: ...
    def get(self, app: str, subject: str, record_id: UUID) -> MemoryRecord | None: ...
    def replace(self, record: MemoryRecord) -> bool: ...
    def list(self, app: str, subject: str) -> tuple[MemoryRecord, ...]: ...
    def delete(self, app: str, subject: str, record_id: UUID) -> bool: ...
    def delete_all(self, app: str, subject: str) -> int: ...


class InMemoryMemoryStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._records = {}

    def put(self, record, *, limit):
        with self._lock:
            bucket = self._records.setdefault((record.app, record.subject), {})
            if len(bucket) >= limit:
                return False
            bucket[record.id] = record
            return True

    def get(self, app, subject, record_id):
        with self._lock:
            return self._records.get((app, subject), {}).get(record_id)

    def replace(self, record):
        with self._lock:
            bucket = self._records.get((record.app, record.subject), {})
            if record.id not in bucket:
                return False
            bucket[record.id] = record
            return True

    def list(self, app, subject):
        with self._lock:
            return tuple(self._records.get((app, subject), {}).values())

    def delete(self, app, subject, record_id):
        with self._lock:
            return self._records.get((app, subject), {}).pop(record_id, None) is not None

    def delete_all(self, app, subject):
        with self._lock:
            return len(self._records.pop((app, subject), {}))


def _terms(text):
    return {word.casefold() for word in _WORD.findall(text) if len(word) > 2}


class MemoryService:
    """Requires an active principal with memory:read / memory:write for its own app."""

    def __init__(self, *, store: MemoryStore | None = None, enabled=False,
                 clock=time.time):
        if type(enabled) is not bool:
            raise ValueError("enabled must be a boolean")
        self.store = store if store is not None else InMemoryMemoryStore()
        self.enabled = enabled
        self.clock = clock

    def _store_call(self, operation, *args, **kwargs):
        # Any storage fault is reported as a stable code; no detail or content leaks.
        try:
            return operation(*args, **kwargs)
        except Exception:
            raise MemoryEngineError("STORE_UNAVAILABLE") from None

    @staticmethod
    def _own(principal, records):
        # Defence in depth against a faulty adapter returning foreign records.
        return tuple(r for r in records if isinstance(r, MemoryRecord) and
                     r.app == principal.app and r.subject == principal.subject)

    @staticmethod
    def _record_id(record_id):
        if type(record_id) is not UUID:
            raise MemoryEngineError("VALIDATION_FAILED")
        return record_id

    def _authorize(self, principal, permission):
        if not self.enabled:
            raise MemoryEngineError("MEMORY_DISABLED")
        now = self.clock()
        if (type(now) not in (int, float) or not math.isfinite(now) or
                not isinstance(principal, Principal) or principal.active is not True or
                type(principal.subject) is not str or
                not 1 <= len(principal.subject) <= 128 or
                principal.app not in APPS or
                type(principal.expires_at) not in (int, float) or
                not principal.expires_at > now):
            raise MemoryEngineError("AUTHENTICATION_INVALID")
        if (type(principal.permissions) is not frozenset or
                permission not in principal.permissions):
            raise MemoryEngineError("AUTHORIZATION_DENIED")
        return now

    @staticmethod
    def _content(content):
        if (type(content) is not str or not content.strip() or
                len(content) > MAX_CONTENT_CHARS or _CREDENTIAL_MARKER.search(content)):
            raise MemoryEngineError("VALIDATION_FAILED")
        return content.strip()

    def remember(self, principal, *, content, kind, user_confirmed,
                 retention_days=DEFAULT_RETENTION_DAYS):
        """Returns the stored record; callers may claim storage only from this receipt."""
        now = self._authorize(principal, "memory:write")
        if user_confirmed is not True:
            raise MemoryEngineError("CONSENT_REQUIRED")
        if (kind not in KINDS or type(retention_days) is not int or
                not 1 <= retention_days <= MAX_RETENTION_DAYS):
            raise MemoryEngineError("VALIDATION_FAILED")
        record = MemoryRecord(
            uuid4(), principal.app, principal.subject, kind, self._content(content),
            now, now, now + retention_days * 86400,
        )
        self._purge_expired(principal, now)
        if not self._store_call(self.store.put, record,
                                limit=MAX_RECORDS_PER_PRINCIPAL):
            raise MemoryEngineError("QUOTA_EXCEEDED")
        return record

    def recall(self, principal, query, *, limit=MAX_RECALL):
        now = self._authorize(principal, "memory:read")
        if (type(query) is not str or not query.strip() or len(query) > 256 or
                type(limit) is not int or not 1 <= limit <= MAX_RECALL):
            raise MemoryEngineError("VALIDATION_FAILED")
        self._purge_expired(principal, now)
        terms = _terms(query)
        scored = []
        for record in self._own(principal, self._store_call(
                self.store.list, principal.app, principal.subject)):
            if record.expires_at <= now:
                continue
            score = len(terms & _terms(record.content))
            if score:
                scored.append((score, record.updated_at, record))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return tuple(record for _, _, record in scored[:limit])

    def update(self, principal, record_id, *, content, user_confirmed):
        now = self._authorize(principal, "memory:write")
        if user_confirmed is not True:
            raise MemoryEngineError("CONSENT_REQUIRED")
        self._record_id(record_id)
        new_content = self._content(content)
        self._purge_expired(principal, now)
        current = self._own(principal, (self._store_call(
            self.store.get, principal.app, principal.subject, record_id),))
        if not current or current[0].id != record_id:
            raise MemoryEngineError("NOT_FOUND")
        updated = replace(current[0], content=new_content, updated_at=now)
        if self._store_call(self.store.replace, updated) is not True:
            raise MemoryEngineError("NOT_FOUND")
        return updated

    def forget(self, principal, record_id):
        self._authorize(principal, "memory:write")
        self._record_id(record_id)
        if self._store_call(self.store.delete, principal.app, principal.subject,
                            record_id) is not True:
            raise MemoryEngineError("NOT_FOUND")

    def forget_all(self, principal):
        """Erasure of everything this principal stored in its own app area."""
        self._authorize(principal, "memory:write")
        count = self._store_call(self.store.delete_all, principal.app, principal.subject)
        if type(count) is not int or count < 0:
            raise MemoryEngineError("STORE_UNAVAILABLE")
        return count

    def _purge_expired(self, principal, now):
        for record in self._own(principal, self._store_call(
                self.store.list, principal.app, principal.subject)):
            if (record.expires_at <= now and self._store_call(
                    self.store.delete, record.app, record.subject, record.id) is not True):
                raise MemoryEngineError("STORE_UNAVAILABLE")

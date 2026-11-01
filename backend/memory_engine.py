"""Fail-closed, consent-based long-term memory preparation.

Memories are explicit user-approved notes, not conversation logs, knowledge
entries or model training data. Every record is isolated by (app, subject).
The in-memory store is volatile and for tests/local preparation only; a
production adapter needs SecurityChain-P0 approval, encryption and a durable,
audited deletion path. Nothing here is wired to an HTTP route.
"""

from dataclasses import dataclass, replace
import heapq
import itertools
import math
import re
import threading
import time
from typing import Protocol
from uuid import UUID, uuid4
import weakref

from ai_support import APPS, Principal


KINDS = frozenset({"preference", "fact"})
MAX_CONTENT_CHARS = 500
MAX_RECORDS_PER_PRINCIPAL = 100
MAX_RECORDS_TOTAL = 10_000
MAX_EXPIRY_JOBS = 10_000
MAX_RECALL = 5
DEFAULT_RETENTION_DAYS = 90
MAX_RETENTION_DAYS = 365
_CREDENTIAL_MARKER = re.compile(
    r"(?i)\b(password|passwd|secret|token|api[\s_-]?key|authorization|bearer)\b"
    r"(?:\s+(?:(?:is|bearer)\s+)?|[:=]\s*)\S+"
)
_WORD = re.compile(r"[^\W_]+", re.UNICODE)
_MEMORY_MUTATION_LOCK = threading.RLock()


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
        self._record_count = 0

    def put(self, record, *, limit):
        with self._lock:
            key = (record.app, record.subject)
            bucket = self._records.get(key, {})
            if (record.id not in bucket and
                    (len(bucket) >= limit or self._record_count >= MAX_RECORDS_TOTAL)):
                return False
            bucket = self._records.setdefault(key, bucket)
            if record.id not in bucket:
                self._record_count += 1
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
            key = (app, subject)
            bucket = self._records.get(key)
            if bucket is None or record_id not in bucket:
                return False
            del bucket[record_id]
            self._record_count -= 1
            if not bucket:
                del self._records[key]
            return True

    def delete_all(self, app, subject):
        with self._lock:
            bucket = self._records.pop((app, subject), {})
            self._record_count -= len(bucket)
            return len(bucket)


class _ExpiryScheduler:
    def __init__(self):
        self._condition = threading.Condition()
        self._queue = []
        self._sequence = itertools.count()
        self._worker = None
        self._pending = 0

    def schedule(self, store, record, delay):
        try:
            store_ref = weakref.ref(store)
        except TypeError:
            store_ref = lambda: store
        with self._condition:
            if self._pending >= MAX_EXPIRY_JOBS:
                raise RuntimeError("expiry queue is full")
            entry = (
                time.monotonic() + max(0, delay), next(self._sequence), store_ref,
                record.app, record.subject, record.id, record.expires_at,
            )
            heapq.heappush(self._queue, entry)
            self._pending += 1
            if self._worker is None:
                worker = threading.Thread(target=self._run, daemon=True)
                try:
                    worker.start()
                except Exception:
                    self._queue.remove(entry)
                    heapq.heapify(self._queue)
                    self._pending -= 1
                    raise
                self._worker = worker
            self._condition.notify()

    def cancel(self, store, app, subject, record_id=None):
        with self._condition:
            remaining = [
                entry for entry in self._queue
                if not (
                    entry[2]() is store and entry[3] == app and
                    entry[4] == subject and
                    (record_id is None or entry[5] == record_id)
                )
            ]
            removed = len(self._queue) - len(remaining)
            if removed:
                self._queue = remaining
                self._pending -= removed
                heapq.heapify(self._queue)
                self._condition.notify()

    def _run(self):
        while True:
            with self._condition:
                if not self._queue:
                    self._worker = None
                    return
                delay = self._queue[0][0] - time.monotonic()
                if delay > 0:
                    self._condition.wait(delay)
                    continue
                _, _, store_ref, app, subject, record_id, expires_at = heapq.heappop(
                    self._queue)
            store = store_ref()
            if store is None:
                self._complete()
                continue
            try:
                retry = False
                with _MEMORY_MUTATION_LOCK:
                    record = store.get(app, subject, record_id)
                    if record is None or record.expires_at != expires_at:
                        pass
                    elif store.delete(app, subject, record_id) is not True:
                        record = store.get(app, subject, record_id)
                        retry = record is not None and record.expires_at == expires_at
                if retry:
                    self._schedule_values(store, app, subject, record_id, expires_at, 60)
                else:
                    self._complete()
            except Exception:
                self._schedule_values(store, app, subject, record_id, expires_at, 60)

    def _complete(self):
        with self._condition:
            self._pending -= 1

    def _schedule_values(self, store, app, subject, record_id, expires_at, delay):
        try:
            store_ref = weakref.ref(store)
        except TypeError:
            store_ref = lambda: store
        with self._condition:
            heapq.heappush(self._queue, (
                time.monotonic() + delay, next(self._sequence), store_ref,
                app, subject, record_id, expires_at,
            ))
            self._condition.notify()


_EXPIRY_SCHEDULER = _ExpiryScheduler()


def _is_finite_number(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except (OverflowError, TypeError):
        return False


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
        self._write_lock = _MEMORY_MUTATION_LOCK

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
        try:
            now = self.clock()
        except Exception:
            raise MemoryEngineError("AUTHENTICATION_INVALID") from None
        if (not _is_finite_number(now) or now < 0 or
                not isinstance(principal, Principal) or principal.active is not True or
                type(principal.subject) is not str or
                not 1 <= len(principal.subject) <= 128 or
                type(principal.app) is not str or
                principal.app not in APPS or
                not _is_finite_number(principal.expires_at) or
                not principal.expires_at > now):
            raise MemoryEngineError("AUTHENTICATION_INVALID")
        if (type(principal.permissions) is not frozenset or
                any(type(item) is not str for item in principal.permissions)):
            raise MemoryEngineError("AUTHENTICATION_INVALID")
        if permission not in principal.permissions:
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
        self._authorize(principal, "memory:write")
        if user_confirmed is not True:
            raise MemoryEngineError("CONSENT_REQUIRED")
        if (type(kind) is not str or kind not in KINDS or
                type(retention_days) is not int or
                not 1 <= retention_days <= MAX_RETENTION_DAYS):
            raise MemoryEngineError("VALIDATION_FAILED")
        content = self._content(content)
        with self._write_lock:
            now = self._authorize(principal, "memory:write")
            record = MemoryRecord(
                uuid4(), principal.app, principal.subject, kind, content,
                now, now, now + retention_days * 86400,
            )
            self._purge_expired(principal, now)
            try:
                _EXPIRY_SCHEDULER.schedule(self.store, record, record.expires_at - now)
            except Exception:
                raise MemoryEngineError("STORE_UNAVAILABLE") from None
            try:
                stored = self._store_call(self.store.put, record,
                                          limit=MAX_RECORDS_PER_PRINCIPAL)
            except MemoryEngineError:
                _EXPIRY_SCHEDULER.cancel(
                    self.store, principal.app, principal.subject, record.id)
                raise
            if stored is False:
                _EXPIRY_SCHEDULER.cancel(
                    self.store, principal.app, principal.subject, record.id)
                raise MemoryEngineError("QUOTA_EXCEEDED")
            if stored is not True:
                _EXPIRY_SCHEDULER.cancel(
                    self.store, principal.app, principal.subject, record.id)
                raise MemoryEngineError("STORE_UNAVAILABLE")
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
        self._authorize(principal, "memory:write")
        if user_confirmed is not True:
            raise MemoryEngineError("CONSENT_REQUIRED")
        self._record_id(record_id)
        new_content = self._content(content)
        with self._write_lock:
            now = self._authorize(principal, "memory:write")
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
        with self._write_lock:
            now = self._authorize(principal, "memory:write")
            self._record_id(record_id)
            self._purge_expired(principal, now)
            if self._store_call(self.store.delete, principal.app, principal.subject,
                                record_id) is not True:
                raise MemoryEngineError("NOT_FOUND")
            _EXPIRY_SCHEDULER.cancel(
                self.store, principal.app, principal.subject, record_id)

    def forget_all(self, principal):
        """Erasure of everything this principal stored in its own app area."""
        with self._write_lock:
            self._authorize(principal, "memory:write")
            count = self._store_call(
                self.store.delete_all, principal.app, principal.subject)
            _EXPIRY_SCHEDULER.cancel(self.store, principal.app, principal.subject)
        if type(count) is not int or count < 0:
            raise MemoryEngineError("STORE_UNAVAILABLE")
        return count

    def _purge_expired(self, principal, now):
        with self._write_lock:
            for record in self._own(principal, self._store_call(
                    self.store.list, principal.app, principal.subject)):
                if record.expires_at <= now and self._store_call(
                        self.store.delete, record.app, record.subject, record.id) is not True:
                    remaining = self._store_call(
                        self.store.get, record.app, record.subject, record.id)
                    if remaining is None:
                        _EXPIRY_SCHEDULER.cancel(
                            self.store, record.app, record.subject, record.id)
                        continue
                    raise MemoryEngineError("STORE_UNAVAILABLE")
                elif record.expires_at <= now:
                    _EXPIRY_SCHEDULER.cancel(
                        self.store, record.app, record.subject, record.id)

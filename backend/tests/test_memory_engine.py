from concurrent.futures import ThreadPoolExecutor
import gc
from pathlib import Path
import sys
import threading
import time
import unittest
import weakref
from unittest.mock import patch
from uuid import uuid4


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_support import Principal
from memory_engine import (
    InMemoryMemoryStore, MAX_RECORDS_PER_PRINCIPAL,
    MemoryEngineError, MemoryRecord, MemoryService as _MemoryService,
    _EXPIRY_SCHEDULER,
    _ExpiryScheduler,
)


def principal(app="niknolig", subject="u1", perms=("memory:read", "memory:write"),
              active=True, expires=2000.0):
    return Principal(subject, app, frozenset(perms), expires, active)


TEST_CONSENT = "test.signed.consent"


class TestConsentVerifier:
    def __init__(self, *, revoked=False, accepted=True, app=None, subject=None,
                 issued_at=0.0, expires_at=10**9):
        self.revoked = revoked
        self.accepted = accepted
        self.app = app
        self.subject = subject
        self.issued_at = issued_at
        self.expires_at = expires_at
        self.calls = []

    def verify(self, principal, evidence, *, purpose, now):
        self.calls.append((principal, evidence, purpose, now))
        return (
            self.accepted and not self.revoked and
            evidence == "test.signed.consent" and
            purpose == "long-term-memory" and
            principal.app in {"niknolig", "niknolig-defense"} and
            bool(principal.subject) and
            (self.app is None or principal.app == self.app) and
            (self.subject is None or principal.subject == self.subject) and
            self.issued_at <= now < self.expires_at
        )


class MemoryService(_MemoryService):
    """Inject a test-only verifier for tests that exercise enabled operations."""

    def __init__(self, *, store=None, enabled=False, clock=time.time,
                 consent_verifier=None):
        if enabled and consent_verifier is None:
            consent_verifier = TestConsentVerifier()
        super().__init__(
            store=store, enabled=enabled, consent_verifier=consent_verifier,
            clock=clock)


def service(enabled=True, store=None, clock=lambda: 1000.0, consent_verifier=None):
    return MemoryService(
        store=store, enabled=enabled,
        consent_verifier=consent_verifier or TestConsentVerifier(), clock=clock)


def code(callable_):
    try:
        callable_()
    except MemoryEngineError as exc:
        return exc.code
    return None


class MemoryEngineTest(unittest.TestCase):
    def test_consent_evidence_rejects_non_token_characters(self):
        verifier = TestConsentVerifier()
        s = service(consent_verifier=verifier)

        self.assertEqual(code(lambda: s.remember(
            principal(), content="alpha beta", kind="fact",
            consent_evidence="test:signed:consent")), "CONSENT_REQUIRED")
        self.assertEqual(verifier.calls, [])

    def test_disabled_by_default(self):
        self.assertEqual(MemoryService().enabled, False)
        self.assertEqual(code(lambda: MemoryService().recall(
            principal(), "x", consent_evidence=TEST_CONSENT)),
                         "MEMORY_DISABLED")

    def test_requires_explicit_consent(self):
        verifier = TestConsentVerifier(accepted=False)
        s = service(consent_verifier=verifier)
        for evidence in (False, None, "yes", 1, "test.signed.consent"):
            self.assertEqual(code(lambda: s.remember(
                principal(), content="Ich mag kurze Antworten", kind="preference",
                consent_evidence=evidence)), "CONSENT_REQUIRED")
        self.assertEqual(verifier.calls[0][2], "long-term-memory")
        self.assertEqual(code(lambda: s.recall(
            principal(), "Antworten", consent_evidence=TEST_CONSENT)),
            "CONSENT_REQUIRED")

    def test_consent_evidence_must_be_current_and_scope_bound(self):
        p = principal()
        for verifier in (
                TestConsentVerifier(revoked=True),
                TestConsentVerifier(expires_at=999.0),
                TestConsentVerifier(app="niknolig-defense"),
                TestConsentVerifier(subject="another-user")):
            s = service(consent_verifier=verifier)
            self.assertEqual(code(lambda: s.remember(
                p, content="alpha beta", kind="fact",
                consent_evidence="test.signed.consent")), "CONSENT_REQUIRED")

        s = _MemoryService(enabled=True, clock=lambda: 1000.0)
        self.assertEqual(code(lambda: s.remember(
            p, content="alpha beta", kind="fact",
            consent_evidence="test.signed.consent")), "CONSENT_REQUIRED")

    def test_revoked_consent_blocks_recall_but_not_erasure(self):
        verifier = TestConsentVerifier()
        s, p = service(consent_verifier=verifier), principal()
        s.remember(
            p, content="alpha beta", kind="fact",
            consent_evidence=TEST_CONSENT)
        verifier.revoked = True
        self.assertEqual(code(lambda: s.recall(
            p, "alpha", consent_evidence=TEST_CONSENT)), "CONSENT_REQUIRED")
        self.assertEqual(s.forget_all(p), 1)

    def test_remember_recall_update_forget(self):
        s, p = service(), principal()
        record = s.remember(p, content="Ich mag kurze Antworten", kind="preference",
                            consent_evidence="test.signed.consent")
        self.assertEqual(s.recall(
            p, "kurze Antworten", consent_evidence=TEST_CONSENT), (record,))
        updated = s.update(p, record.id, content="Ich mag ausführliche Antworten",
                           consent_evidence="test.signed.consent")
        self.assertEqual(s.recall(p, "kurze", consent_evidence=TEST_CONSENT), ())
        self.assertEqual(s.recall(
            p, "ausführliche", consent_evidence=TEST_CONSENT)[0].id, updated.id)
        s.forget(p, record.id)
        self.assertEqual(s.recall(
            p, "ausführliche", consent_evidence=TEST_CONSENT), ())
        self.assertEqual(code(lambda: s.forget(p, record.id)), "NOT_FOUND")

    def test_recall_normalizes_unicode_queries(self):
        s, p = service(), principal()
        record = s.remember(
            p, content="ｋｕｒｚｅ Mäuse", kind="preference",
            consent_evidence="test.signed.consent")
        self.assertEqual(s.recall(
            p, "ｋｕｒｚｅ", consent_evidence=TEST_CONSENT), (record,))
        self.assertEqual(s.recall(
            p, "Ma\u0308use", consent_evidence=TEST_CONSENT), (record,))

    def test_isolation_between_apps_and_subjects(self):
        s = service()
        a = principal()
        record = s.remember(a, content="Lieblingsfarbe Grün", kind="fact",
                            consent_evidence="test.signed.consent")
        for other in (principal(app="niknolig-defense"), principal(subject="u2")):
            self.assertEqual(s.recall(
                other, "Lieblingsfarbe", consent_evidence=TEST_CONSENT), ())
            self.assertEqual(code(lambda: s.forget(other, record.id)), "NOT_FOUND")
            self.assertEqual(s.forget_all(other), 0)
        self.assertEqual(len(s.recall(
            a, "Lieblingsfarbe", consent_evidence=TEST_CONSENT)), 1)

    def test_permissions_and_identity(self):
        s = service()
        self.assertEqual(code(lambda: s.remember(
            principal(perms=("memory:read",)), content="x y z", kind="fact",
            consent_evidence="test.signed.consent")), "AUTHORIZATION_DENIED")
        self.assertEqual(code(lambda: s.recall(
            principal(perms=()), "abc", consent_evidence=TEST_CONSENT)),
                         "AUTHORIZATION_DENIED")
        for bad in (principal(active=False), principal(expires=999.0),
                    principal(expires=float("inf")), principal(expires=float("nan")),
                    principal(expires=10**10000), principal(app="other"),
                    principal(app=[]), principal(perms=("memory:read", 1)), None):
            self.assertEqual(code(lambda: s.recall(
                bad, "abc", consent_evidence=TEST_CONSENT)), "AUTHENTICATION_INVALID")
        self.assertEqual(code(lambda: service(
            enabled=True, clock=lambda: -1).recall(
                principal(), "abc", consent_evidence=TEST_CONSENT)),
            "AUTHENTICATION_INVALID")

    def test_expired_principal_cannot_write_update_or_delete(self):
        s, owner = service(), principal()
        record = s.remember(owner, content="alpha beta", kind="fact",
                            consent_evidence="test.signed.consent")
        expired = principal(expires=999.0)
        self.assertEqual(code(lambda: s.remember(
            expired, content="gamma delta", kind="fact",
            consent_evidence="test.signed.consent")),
            "AUTHENTICATION_INVALID")
        self.assertEqual(code(lambda: s.update(
            expired, record.id, content="gamma delta",
            consent_evidence="test.signed.consent")),
            "AUTHENTICATION_INVALID")
        self.assertEqual(code(lambda: s.forget(expired, record.id)),
                         "AUTHENTICATION_INVALID")
        self.assertEqual(s.store.get(owner.app, owner.subject, record.id), record)
        self.assertEqual(len(s.store.list(owner.app, owner.subject)), 1)

    def test_rejects_credentials_and_oversize(self):
        s, p = service(), principal()
        for content in (
                "password: " + uuid4().hex,
                "password is " + uuid4().hex,
                "Bearer " + uuid4().hex,
                "api_key=" + uuid4().hex,
                "Kontakt: person@example.com",
                "Ruf mich an: +1 (415) 555-2671",
                "Kartennummer: 4111 1111 1111 1111",
                "ｐａｓｓｗｏｒｄ＝" + uuid4().hex,
                "private\u202econtent",
                "", "x" * 501, 5):
            self.assertEqual(code(lambda: s.remember(
                p, content=content, kind="fact",
                consent_evidence="test.signed.consent")),
                "VALIDATION_FAILED")
        normalized = s.remember(
            p, content="ｋｕｒｚｅ Antworten", kind="preference",
            consent_evidence="test.signed.consent")
        self.assertEqual(normalized.content, "kurze Antworten")
        self.assertEqual(code(lambda: s.remember(
            p, content="ok ok", kind="secret",
            consent_evidence="test.signed.consent")), "VALIDATION_FAILED")
        self.assertEqual(code(lambda: s.remember(
            p, content="ok ok", kind=[],
            consent_evidence="test.signed.consent")), "VALIDATION_FAILED")

    def test_retention_expiry(self):
        now = [1000.0]
        s = service(clock=lambda: now[0])
        p = principal(expires=10**9)
        s.remember(p, content="Termin Montag", kind="fact",
                   consent_evidence="test.signed.consent",
                   retention_days=1)
        self.assertEqual(len(s.recall(
            p, "Termin", consent_evidence=TEST_CONSENT)), 1)
        now[0] += 86401
        self.assertEqual(s.recall(
            p, "Termin", consent_evidence=TEST_CONSENT), ())

    def test_quota_and_erasure(self):
        s, p = service(), principal()
        for i in range(MAX_RECORDS_PER_PRINCIPAL):
            s.remember(p, content=f"note {i}", kind="fact",
                       consent_evidence="test.signed.consent")
        self.assertEqual(code(lambda: s.remember(
            p, content="one more", kind="fact",
            consent_evidence="test.signed.consent")), "QUOTA_EXCEEDED")
        self.assertEqual(s.forget_all(p), MAX_RECORDS_PER_PRINCIPAL)

    def test_concurrent_writes_respect_per_principal_quota(self):
        s, p = service(), principal()

        def remember(index):
            try:
                return s.remember(
                    p, content=f"note number {index}", kind="fact",
                    consent_evidence="test.signed.consent",
                )
            except MemoryEngineError as exc:
                return exc.code

        with ThreadPoolExecutor(max_workers=32) as pool:
            results = list(pool.map(remember, range(MAX_RECORDS_PER_PRINCIPAL + 20)))
        self.assertEqual(sum(isinstance(item, str) for item in results), 20)
        self.assertTrue(all(item == "QUOTA_EXCEEDED" for item in results
                            if isinstance(item, str)))
        self.assertEqual(len(s.store.list(p.app, p.subject)), MAX_RECORDS_PER_PRINCIPAL)
        self.assertEqual(s.forget_all(p), MAX_RECORDS_PER_PRINCIPAL)

    def test_concurrent_writes_respect_global_store_limit(self):
        store = InMemoryMemoryStore()
        s = MemoryService(store=store, enabled=True, clock=lambda: 1000.0)
        people = [principal(subject=f"global-{index}") for index in range(20)]

        def remember(person):
            try:
                return s.remember(
                    person, content="alpha beta", kind="fact",
                    consent_evidence="test.signed.consent")
            except MemoryEngineError as exc:
                return exc.code

        with patch("memory_engine.MAX_RECORDS_TOTAL", 5):
            with ThreadPoolExecutor(max_workers=20) as pool:
                results = list(pool.map(remember, people))
            self.assertEqual(sum(not isinstance(item, str) for item in results), 5)
            self.assertEqual(
                [item for item in results if isinstance(item, str)],
                ["QUOTA_EXCEEDED"] * 15,
            )
            self.assertEqual(store._record_count, 5)
            for person in people:
                s.forget_all(person)
        self.assertEqual(store._record_count, 0)

    def test_concurrent_forget_all_cannot_cancel_pending_expiry(self):
        class BlockingStore(InMemoryMemoryStore):
            def __init__(self):
                super().__init__()
                self.put_started = threading.Event()
                self.release_put = threading.Event()
                self.delete_all_started = threading.Event()

            def put(self, record, *, limit):
                self.put_started.set()
                if not self.release_put.wait(2):
                    raise RuntimeError("test write timed out")
                return super().put(record, limit=limit)

            def delete_all(self, app, subject):
                self.delete_all_started.set()
                return super().delete_all(app, subject)

        store = BlockingStore()
        writer = MemoryService(store=store, enabled=True, clock=lambda: 1000.0)
        eraser = MemoryService(store=store, enabled=True, clock=lambda: 1000.0)
        p = principal()
        with ThreadPoolExecutor(max_workers=2) as pool:
            write = pool.submit(
                writer.remember, p, content="alpha beta", kind="fact",
                consent_evidence="test.signed.consent")
            self.assertTrue(store.put_started.wait(1))
            erase = pool.submit(eraser.forget_all, p)
            self.assertFalse(store.delete_all_started.wait(0.05))
            store.release_put.set()
            record = write.result(timeout=2)
            self.assertTrue(store.delete_all_started.wait(1))
            self.assertEqual(erase.result(timeout=2), 1)
        self.assertIsNone(store.get(p.app, p.subject, record.id))
        with _EXPIRY_SCHEDULER._condition:
            self.assertFalse(any(
                entry[2]() is store for entry in _EXPIRY_SCHEDULER._queue))


class FaultyStore(InMemoryMemoryStore):
    def __init__(self, **faults):
        super().__init__()
        self.faults = faults

    def put(self, record, *, limit):
        if self.faults.get("put_lies_true"):
            return True
        if "put_after_write" in self.faults:
            super().put(record, limit=limit)
            receipt = self.faults["put_after_write"]
            if receipt == "raise":
                raise RuntimeError("secret-detail")
            return receipt
        if self.faults.get("put") == "raise":
            raise RuntimeError("secret-detail")
        if "put" in self.faults:
            return self.faults["put"]
        return super().put(record, limit=limit)

    def delete(self, app, subject, record_id):
        if self.faults.get("delete_lies_true"):
            return True
        if self.faults.get("delete") == "raise":
            raise RuntimeError("secret-detail")
        if self.faults.get("delete") == "false":
            return False
        return super().delete(app, subject, record_id)

    def delete_all(self, app, subject):
        if self.faults.get("delete_all"):
            raise RuntimeError("secret-detail")
        if "delete_all_receipt" in self.faults:
            return self.faults["delete_all_receipt"]
        return super().delete_all(app, subject)

    def get(self, app, subject, record_id):
        if self.faults.get("get") == "raise":
            raise RuntimeError("secret-detail")
        return super().get(app, subject, record_id)

    def replace(self, record):
        if self.faults.get("replace_lies_true"):
            return True
        if self.faults.get("replace") == "raise":
            raise RuntimeError("secret-detail")
        return super().replace(record)

    def list(self, app, subject):
        if self.faults.get("list") == "raise":
            raise RuntimeError("secret-detail")
        if self.faults.get("foreign"):
            return tuple(r for recs in self._records.values() for r in recs.values())
        return super().list(app, subject)


class MemoryEngineSecurityTest(unittest.TestCase):
    def test_write_failures_and_invalid_store_receipts_fail_closed(self):
        p = principal()
        for fault in ("raise", "unexpected"):
            store = FaultyStore(put=fault)
            s = MemoryService(store=store, enabled=True, clock=lambda: 1000.0)
            self.assertEqual(code(lambda: s.remember(
                p, content="alpha beta", kind="fact",
                consent_evidence="test.signed.consent")),
                "STORE_UNAVAILABLE")
            self.assertEqual(store.list(p.app, p.subject), ())

        store = FaultyStore(put=False)
        s = MemoryService(store=store, enabled=True, clock=lambda: 1000.0)
        self.assertEqual(code(lambda: s.remember(
            p, content="alpha beta", kind="fact",
            consent_evidence="test.signed.consent")),
            "QUOTA_EXCEEDED")
        self.assertEqual(store.list(p.app, p.subject), ())

    def test_read_and_update_storage_errors_fail_closed_without_details(self):
        p = principal()
        store = FaultyStore()
        s = MemoryService(store=store, enabled=True, clock=lambda: 1000.0)
        record = s.remember(p, content="alpha beta", kind="fact",
                            consent_evidence="test.signed.consent")
        for fault, operation in (
                ("get", lambda: s.update(
                    p, record.id, content="gamma delta",
                    consent_evidence="test.signed.consent")),
                ("list", lambda: s.recall(
                    p, "alpha", consent_evidence=TEST_CONSENT)),
                ("replace", lambda: s.update(
                    p, record.id, content="gamma delta",
                    consent_evidence="test.signed.consent"))):
            store.faults = {fault: "raise"}
            with self.assertRaises(MemoryEngineError) as ctx:
                operation()
            self.assertEqual(ctx.exception.code, "STORE_UNAVAILABLE")
            self.assertNotIn("secret-detail", repr(ctx.exception))
            self.assertIsNone(ctx.exception.__cause__)

    def test_partial_write_failure_rolls_back_or_keeps_expiry_cleanup(self):
        p = principal()
        store = FaultyStore(put_after_write="raise", delete="raise")
        s = MemoryService(store=store, enabled=True, clock=lambda: 1000.0)
        self.assertEqual(code(lambda: s.remember(
            p, content="alpha beta", kind="fact",
            consent_evidence="test.signed.consent")),
            "STORE_UNAVAILABLE")
        persisted = store.list(p.app, p.subject)
        self.assertEqual(len(persisted), 1)
        with _EXPIRY_SCHEDULER._condition:
            self.assertTrue(any(
                entry[2]() is store and entry[3] == p.app and
                entry[4] == p.subject and entry[5] == persisted[0].id
                for entry in _EXPIRY_SCHEDULER._queue))
        store.faults.pop("delete")
        self.assertIsNone(s.forget(p, persisted[0].id))
        self.assertEqual(store.list(p.app, p.subject), ())

    def test_partial_write_with_unconfirmed_receipts_is_rolled_back(self):
        p = principal()
        for receipt, expected in ((False, "QUOTA_EXCEEDED"),
                                  ("unexpected", "STORE_UNAVAILABLE")):
            store = FaultyStore(put_after_write=receipt)
            s = MemoryService(store=store, enabled=True, clock=lambda: 1000.0)
            self.assertEqual(code(lambda: s.remember(
                p, content="alpha beta", kind="fact",
                consent_evidence="test.signed.consent")),
                expected)
            self.assertEqual(store.list(p.app, p.subject), ())
            with _EXPIRY_SCHEDULER._condition:
                self.assertFalse(any(
                    entry[2]() is store for entry in _EXPIRY_SCHEDULER._queue))

    def test_successful_looking_mutation_receipts_are_verified(self):
        p = principal()
        store = FaultyStore(put_lies_true=True)
        s = MemoryService(store=store, enabled=True, clock=lambda: 1000.0)
        self.assertEqual(code(lambda: s.remember(
            p, content="alpha beta", kind="fact",
            consent_evidence="test.signed.consent")),
            "STORE_UNAVAILABLE")
        self.assertEqual(store.list(p.app, p.subject), ())

        store = FaultyStore()
        s = MemoryService(store=store, enabled=True, clock=lambda: 1000.0)
        record = s.remember(
            p, content="alpha beta", kind="fact",
            consent_evidence="test.signed.consent")
        store.faults["replace_lies_true"] = True
        self.assertEqual(code(lambda: s.update(
            p, record.id, content="gamma delta",
            consent_evidence="test.signed.consent")),
            "STORE_UNAVAILABLE")
        self.assertEqual(store.get(p.app, p.subject, record.id), record)

        store.faults["delete_lies_true"] = True
        self.assertEqual(code(lambda: s.forget(p, record.id)), "STORE_UNAVAILABLE")
        self.assertIsNotNone(store.get(p.app, p.subject, record.id))
        with _EXPIRY_SCHEDULER._condition:
            self.assertTrue(any(
                entry[2]() is store and entry[5] == record.id
                for entry in _EXPIRY_SCHEDULER._queue))
        store.faults.pop("delete_lies_true")
        self.assertIsNone(s.forget(p, record.id))

    def test_unconfirmed_bulk_deletion_preserves_expiry_cleanup(self):
        store = FaultyStore(delete_all_receipt=1)
        s = MemoryService(store=store, enabled=True, clock=lambda: 1000.0)
        p = principal()
        record = s.remember(
            p, content="alpha beta", kind="fact",
            consent_evidence="test.signed.consent")
        self.assertEqual(code(lambda: s.forget_all(p)), "STORE_UNAVAILABLE")
        self.assertIsNotNone(store.get(p.app, p.subject, record.id))
        with _EXPIRY_SCHEDULER._condition:
            self.assertTrue(any(
                entry[2]() is store and entry[5] == record.id
                for entry in _EXPIRY_SCHEDULER._queue))
        store.faults.pop("delete_all_receipt")
        self.assertEqual(s.forget_all(p), 1)

    def test_expiry_worker_retries_a_false_successful_delete(self):
        class LyingDeleteStore(InMemoryMemoryStore):
            def __init__(self):
                super().__init__()
                self.delete_called = threading.Event()

            def delete(self, app, subject, record_id):
                self.delete_called.set()
                return True

        scheduler = _ExpiryScheduler()
        store = LyingDeleteStore()
        record = MemoryRecord(
            uuid4(), "niknolig", "u1", "fact", "private old plaintext", 1, 1, 100,
        )
        store.put(record, limit=10)
        try:
            scheduler.schedule(store, record, 0.05)
            self.assertTrue(store.delete_called.wait(1))
            self.assertIsNotNone(store.get(record.app, record.subject, record.id))
            deadline = time.monotonic() + 1
            while time.monotonic() < deadline:
                with scheduler._condition:
                    if any(entry[5] == record.id for entry in scheduler._queue):
                        break
                time.sleep(0.01)
            with scheduler._condition:
                self.assertTrue(any(entry[5] == record.id for entry in scheduler._queue))
        finally:
            scheduler.cancel(store, record.app, record.subject)

    def test_dead_stores_do_not_consume_expiry_capacity(self):
        scheduler = _ExpiryScheduler()
        expired_store = InMemoryMemoryStore()
        expired_record = MemoryRecord(
            uuid4(), "niknolig", "u1", "fact", "old content", 1, 1, 100,
        )
        scheduler.schedule(expired_store, expired_record, 3600)
        store_ref = weakref.ref(expired_store)
        del expired_store
        gc.collect()
        self.assertIsNone(store_ref())

        live_store = InMemoryMemoryStore()
        live_record = MemoryRecord(
            uuid4(), "niknolig", "u2", "fact", "new content", 1, 1, 100,
        )
        try:
            with patch("memory_engine.MAX_EXPIRY_JOBS", 1):
                scheduler.schedule(live_store, live_record, 3600)
            self.assertEqual(scheduler._pending, 1)
            self.assertEqual(len(scheduler._queue), 1)
            self.assertIs(scheduler._queue[0][2](), live_store)
        finally:
            with scheduler._condition:
                scheduler._queue.clear()
                scheduler._pending = 0
                scheduler._condition.notify_all()

    def test_expiry_worker_releases_deleted_plaintext_before_waiting(self):
        scheduler = _ExpiryScheduler()
        store = InMemoryMemoryStore()
        first = MemoryRecord(
            uuid4(), "niknolig", "u1", "fact", "private old plaintext", 1, 1, 100,
        )
        later = MemoryRecord(
            uuid4(), "niknolig", "u1", "fact", "later note", 1, 1, 200,
        )
        store.put(first, limit=10)
        store.put(later, limit=10)
        first_id = first.id
        first_ref = weakref.ref(first)
        scheduler.schedule(store, first, 0.05)
        scheduler.schedule(store, later, 3600)
        del first
        deadline = time.monotonic() + 1
        while store.get("niknolig", "u1", first_id) is not None:
            if time.monotonic() >= deadline:
                self.fail("scheduled expiry did not delete the record")
            time.sleep(0.01)
        try:
            deadline = time.monotonic() + 1
            while first_ref() is not None and time.monotonic() < deadline:
                gc.collect()
                time.sleep(0.01)
            self.assertIsNone(first_ref())
        finally:
            scheduler.cancel(store, "niknolig", "u1")

    def test_expiry_scheduler_failure_prevents_write(self):
        store = InMemoryMemoryStore()
        s = MemoryService(store=store, enabled=True, clock=lambda: 1000.0)
        p = principal()
        with patch.object(_EXPIRY_SCHEDULER, "schedule",
                          side_effect=RuntimeError("scheduler unavailable")):
            self.assertEqual(code(lambda: s.remember(
                p, content="alpha beta", kind="fact",
                consent_evidence="test.signed.consent")),
                "STORE_UNAVAILABLE")
        self.assertEqual(store.list(p.app, p.subject), ())
        with patch("memory_engine.MAX_EXPIRY_JOBS", 0):
            self.assertEqual(code(lambda: s.remember(
                p, content="alpha beta", kind="fact",
                consent_evidence="test.signed.consent")),
                "STORE_UNAVAILABLE")
        self.assertEqual(store.list(p.app, p.subject), ())

    def test_total_memory_limit_and_deleted_state_are_bounded(self):
        store = InMemoryMemoryStore()
        s = MemoryService(store=store, enabled=True, clock=lambda: 1000.0)
        principals = [principal(subject=f"user-{i}") for i in range(3)]
        with patch("memory_engine.MAX_RECORDS_TOTAL", 2):
            records = [
                s.remember(p, content="alpha beta", kind="fact",
                           consent_evidence="test.signed.consent")
                for p in principals[:2]
            ]
            self.assertEqual(code(lambda: s.remember(
                principals[2], content="alpha beta", kind="fact",
                consent_evidence="test.signed.consent")), "QUOTA_EXCEEDED")
            s.forget(principals[0], records[0].id)
            self.assertNotIn((principals[0].app, principals[0].subject), store._records)
            s.remember(
                principals[2], content="alpha beta", kind="fact",
                consent_evidence="test.signed.consent")
            s.forget_all(principals[1])
            s.forget_all(principals[2])
        self.assertEqual(store._records, {})
        with _EXPIRY_SCHEDULER._condition:
            self.assertFalse(any(
                entry[2]() is store for entry in _EXPIRY_SCHEDULER._queue))

    def test_create_delete_churn_does_not_leave_buckets_or_jobs(self):
        store = InMemoryMemoryStore()
        s = MemoryService(store=store, enabled=True, clock=lambda: 1000.0)
        for index in range(250):
            p = principal(subject=f"user-{index}")
            record = s.remember(
                p, content="alpha beta", kind="fact",
                consent_evidence="test.signed.consent")
            s.forget(p, record.id)
        self.assertEqual(store._records, {})
        with _EXPIRY_SCHEDULER._condition:
            self.assertFalse(any(
                entry[2]() is store for entry in _EXPIRY_SCHEDULER._queue))

    def test_update_requires_consent_and_valid_id(self):
        s, p = service(), principal()
        r = s.remember(p, content="alpha beta", kind="fact",
                       consent_evidence="test.signed.consent")
        self.assertEqual(code(lambda: s.update(
            p, r.id, content="neu neu", consent_evidence=False)),
            "CONSENT_REQUIRED")
        for bad in (str(r.id), "../x", None, 1):
            self.assertEqual(code(lambda: s.update(
                p, bad, content="neu neu",
                consent_evidence="test.signed.consent")), "VALIDATION_FAILED")
            self.assertEqual(code(lambda: s.forget(p, bad)), "VALIDATION_FAILED")
        self.assertEqual(code(lambda: s.update(
            p, uuid4(), content="neu neu",
            consent_evidence="test.signed.consent")), "NOT_FOUND")
        self.assertEqual(s.recall(
            p, "alpha", consent_evidence=TEST_CONSENT)[0].content, "alpha beta")

    def test_update_rejects_obvious_sensitive_identifiers_without_mutation(self):
        s, p = service(), principal()
        record = s.remember(p, content="alpha beta", kind="fact",
                            consent_evidence="test.signed.consent")
        self.assertEqual(code(lambda: s.update(
            p, record.id, content="Mail me person@example.com",
            consent_evidence="test.signed.consent")), "VALIDATION_FAILED")
        self.assertEqual(s.store.get(p.app, p.subject, record.id), record)

    def test_cross_app_cannot_update_or_delete(self):
        s = service()
        a, d = principal(), principal(app="niknolig-defense")
        r = s.remember(a, content="alpha beta", kind="fact",
                       consent_evidence="test.signed.consent")
        self.assertEqual(code(lambda: s.update(
            d, r.id, content="x y z",
            consent_evidence="test.signed.consent")), "NOT_FOUND")
        self.assertEqual(code(lambda: s.forget(d, r.id)), "NOT_FOUND")
        self.assertEqual(s.recall(
            a, "alpha", consent_evidence=TEST_CONSENT)[0].content, "alpha beta")

    def test_expired_records_are_physically_removed(self):
        now = [1000.0]
        store = InMemoryMemoryStore()
        s = MemoryService(store=store, enabled=True, clock=lambda: now[0])
        p = principal(expires=10**9)
        s.remember(p, content="alpha beta", kind="fact",
                   consent_evidence="test.signed.consent",
                   retention_days=1)
        now[0] += 86401
        s.recall(p, "alpha", consent_evidence=TEST_CONSENT)
        self.assertEqual(store.list(p.app, p.subject), ())

    def test_expiration_is_scheduled_without_user_activity(self):
        store = InMemoryMemoryStore()
        s = MemoryService(store=store, enabled=True, clock=lambda: 1000.0)
        p = principal(expires=10**9)

        original_schedule = _EXPIRY_SCHEDULER.schedule

        def schedule_after_short_delay(target_store, target_record, delay):
            self.assertEqual(delay, 86400.0)
            original_schedule(target_store, target_record, 0.1)

        with patch.object(_EXPIRY_SCHEDULER, "schedule",
                          side_effect=schedule_after_short_delay) as schedule:
            record = s.remember(p, content="alpha beta", kind="fact",
                                consent_evidence="test.signed.consent",
                                retention_days=1)
            schedule.assert_called_once_with(store, record, 86400.0)
        deadline = time.monotonic() + 1
        while store.get(p.app, p.subject, record.id) is not None:
            if time.monotonic() >= deadline:
                self.fail("scheduled expiry did not delete the record")
            time.sleep(0.01)

    def test_forget_purges_other_expired_records(self):
        now = [1000.0]
        store = InMemoryMemoryStore()
        s = MemoryService(store=store, enabled=True, clock=lambda: now[0])
        p = principal(expires=10**9)
        expired = s.remember(p, content="old note", kind="fact",
                             consent_evidence="test.signed.consent",
                             retention_days=1)
        now[0] += 86401
        current = s.remember(p, content="current note", kind="fact",
                             consent_evidence="test.signed.consent",
                             retention_days=1)
        s.forget(p, current.id)
        self.assertIsNone(store.get(p.app, p.subject, expired.id))
        self.assertEqual(store.list(p.app, p.subject), ())

    def test_deletion_failures_are_not_reported_as_success(self):
        for fault in ("raise", "false"):
            store = FaultyStore()
            s = MemoryService(store=store, enabled=True, clock=lambda: 1000.0)
            p = principal()
            r = s.remember(p, content="alpha beta", kind="fact",
                           consent_evidence="test.signed.consent")
            store.faults["delete"] = fault
            self.assertEqual(code(lambda: s.forget(p, r.id)), "STORE_UNAVAILABLE")
            self.assertEqual(len(store.list(p.app, p.subject)), 1)
        store.faults = {"delete_all": True}
        self.assertEqual(code(lambda: s.forget_all(p)), "STORE_UNAVAILABLE")

    def test_invalid_forget_all_receipt_preserves_expiry_jobs(self):
        store = FaultyStore(delete_all_receipt=None)
        s = MemoryService(store=store, enabled=True, clock=lambda: 1000.0)
        p = principal()
        record = s.remember(
            p, content="alpha beta", kind="fact",
            consent_evidence="test.signed.consent")
        self.assertEqual(code(lambda: s.forget_all(p)), "STORE_UNAVAILABLE")
        self.assertIsNotNone(store.get(p.app, p.subject, record.id))
        with _EXPIRY_SCHEDULER._condition:
            self.assertTrue(any(
                entry[2]() is store and entry[5] == record.id
                for entry in _EXPIRY_SCHEDULER._queue))
        store.faults.pop("delete_all_receipt")
        self.assertEqual(s.forget_all(p), 1)
        self.assertIsNone(store.get(p.app, p.subject, record.id))

    def test_invalid_forget_all_verification_preserves_expiry_jobs(self):
        for final_listing in (None, False):
            class UnverifiableListStore(InMemoryMemoryStore):
                def __init__(self):
                    super().__init__()
                    self.delete_all_called = False

                def delete_all(self, app, subject):
                    self.delete_all_called = True
                    return len(super().list(app, subject))

                def list(self, app, subject):
                    if self.delete_all_called:
                        return final_listing
                    return super().list(app, subject)

            with self.subTest(final_listing=final_listing):
                store = UnverifiableListStore()
                s = MemoryService(store=store, enabled=True, clock=lambda: 1000.0)
                p = principal()
                record = s.remember(
                    p, content="alpha beta", kind="fact",
                    consent_evidence="test.signed.consent")
                self.assertEqual(
                    code(lambda: s.forget_all(p)), "STORE_UNAVAILABLE")
                self.assertIsNotNone(store.get(p.app, p.subject, record.id))
                with _EXPIRY_SCHEDULER._condition:
                    self.assertTrue(any(
                        entry[2]() is store and entry[5] == record.id
                        for entry in _EXPIRY_SCHEDULER._queue))

    def test_expired_purge_failure_fails_closed_without_leaking(self):
        now = [1000.0]
        store = FaultyStore()
        s = MemoryService(store=store, enabled=True, clock=lambda: now[0])
        p = principal(expires=10**9)
        s.remember(p, content="alpha beta", kind="fact",
                   consent_evidence="test.signed.consent",
                   retention_days=1)
        now[0] += 86401
        store.faults["delete"] = "raise"
        with self.assertRaises(MemoryEngineError) as ctx:
            s.recall(p, "alpha", consent_evidence=TEST_CONSENT)
        self.assertEqual(ctx.exception.code, "STORE_UNAVAILABLE")
        self.assertNotIn("secret-detail", repr(ctx.exception))
        self.assertIsNone(ctx.exception.__cause__)

    def test_concurrent_expiry_cleanup_is_not_store_failure(self):
        class ConcurrentDeleteStore(InMemoryMemoryStore):
            def __init__(self):
                super().__init__()
                self.expired_listed = threading.Event()
                self.finish_list = threading.Event()
                self.block_expiry_list = False

            def list(self, app, subject):
                records = super().list(app, subject)
                if self.block_expiry_list:
                    self.expired_listed.set()
                    if not self.finish_list.wait(2):
                        raise RuntimeError("concurrent delete test timed out")
                return records

        now = [1000.0]
        store = ConcurrentDeleteStore()
        s = MemoryService(store=store, enabled=True, clock=lambda: now[0])
        p = principal(expires=10**9)
        record = s.remember(p, content="alpha beta", kind="fact",
                            consent_evidence="test.signed.consent",
                            retention_days=1)
        now[0] += 86401
        store.block_expiry_list = True
        with ThreadPoolExecutor(max_workers=1) as pool:
            recall = pool.submit(
                s.recall, p, "alpha", consent_evidence=TEST_CONSENT)
            self.assertTrue(store.expired_listed.wait(1))
            self.assertTrue(store.delete(p.app, p.subject, record.id))
            store.finish_list.set()
            self.assertEqual(recall.result(timeout=2), ())
        self.assertEqual(store.list(p.app, p.subject), ())

    def test_recall_rechecks_authorization_and_expiry_after_slow_cleanup(self):
        class BlockingListStore(InMemoryMemoryStore):
            def __init__(self):
                super().__init__()
                self.block_list = False
                self.list_started = threading.Event()
                self.release_list = threading.Event()

            def list(self, app, subject):
                records = super().list(app, subject)
                if self.block_list:
                    self.list_started.set()
                    if not self.release_list.wait(2):
                        raise RuntimeError("slow recall test timed out")
                return records

        for advance, principal_expiry, expected in (
                (2, 1001.0, "AUTHENTICATION_INVALID"),
                (86401, 10**9, ())):
            with self.subTest(expected=expected):
                now = [1000.0]
                store = BlockingListStore()
                s = MemoryService(store=store, enabled=True, clock=lambda: now[0])
                p = principal(expires=principal_expiry)
                record = s.remember(
                    p, content="alpha beta", kind="fact",
                    consent_evidence="test.signed.consent",
                    retention_days=1)
                store.block_list = True

                def recall():
                    try:
                        return s.recall(
                            p, "alpha", consent_evidence=TEST_CONSENT)
                    except MemoryEngineError as exc:
                        return exc.code

                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(recall)
                    self.assertTrue(store.list_started.wait(1))
                    now[0] += advance
                    store.release_list.set()
                    result = future.result(timeout=2)
                if expected == "AUTHENTICATION_INVALID":
                    self.assertEqual(result, expected)
                else:
                    self.assertEqual(result, ())
                    self.assertIsNotNone(store.get(p.app, p.subject, record.id))

    def test_foreign_records_from_faulty_store_are_ignored(self):
        store = FaultyStore()
        s = MemoryService(store=store, enabled=True, clock=lambda: 1000.0)
        s.remember(principal(app="niknolig-defense"), content="alpha beta",
                   kind="fact", consent_evidence="test.signed.consent")
        store.faults["foreign"] = True
        self.assertEqual(s.recall(
            principal(), "alpha", consent_evidence=TEST_CONSENT), ())


class MemoryNotExposedTest(unittest.TestCase):
    def test_no_http_wiring_and_controls_stay_closed(self):
        from ai_support import RuntimeControls
        import asgi
        self.assertFalse(RuntimeControls().available())
        paths = {route.path for route in asgi.create_app().routes}
        self.assertFalse([x for x in paths if "memor" in x.lower()])
        root = Path(__file__).resolve().parents[1]
        for name in ("asgi.py", "app.py", "support_http.py", "ai_support.py"):
            self.assertNotIn("memory_engine", (root / name).read_text("utf-8"))


if __name__ == "__main__":
    unittest.main()

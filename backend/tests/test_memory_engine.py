from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import threading
import time
import unittest
from unittest.mock import patch
from uuid import uuid4


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_support import Principal
from memory_engine import (
    InMemoryMemoryStore, MAX_RECORDS_PER_PRINCIPAL, MemoryEngineError, MemoryService,
    _EXPIRY_SCHEDULER,
)


def principal(app="niknolig", subject="u1", perms=("memory:read", "memory:write"),
              active=True, expires=2000.0):
    return Principal(subject, app, frozenset(perms), expires, active)


def service(enabled=True):
    return MemoryService(enabled=enabled, clock=lambda: 1000.0)


def code(callable_):
    try:
        callable_()
    except MemoryEngineError as exc:
        return exc.code
    return None


class MemoryEngineTest(unittest.TestCase):
    def test_disabled_by_default(self):
        self.assertEqual(MemoryService().enabled, False)
        self.assertEqual(code(lambda: MemoryService().recall(principal(), "x")),
                         "MEMORY_DISABLED")

    def test_requires_explicit_consent(self):
        s = service()
        for flag in (False, None, "yes", 1):
            self.assertEqual(code(lambda: s.remember(
                principal(), content="Ich mag kurze Antworten", kind="preference",
                user_confirmed=flag)), "CONSENT_REQUIRED")
        self.assertEqual(s.recall(principal(), "Antworten"), ())

    def test_remember_recall_update_forget(self):
        s, p = service(), principal()
        record = s.remember(p, content="Ich mag kurze Antworten", kind="preference",
                            user_confirmed=True)
        self.assertEqual(s.recall(p, "kurze Antworten"), (record,))
        updated = s.update(p, record.id, content="Ich mag ausführliche Antworten",
                           user_confirmed=True)
        self.assertEqual(s.recall(p, "kurze"), ())
        self.assertEqual(s.recall(p, "ausführliche")[0].id, updated.id)
        s.forget(p, record.id)
        self.assertEqual(s.recall(p, "ausführliche"), ())
        self.assertEqual(code(lambda: s.forget(p, record.id)), "NOT_FOUND")

    def test_isolation_between_apps_and_subjects(self):
        s = service()
        a = principal()
        record = s.remember(a, content="Lieblingsfarbe Grün", kind="fact",
                            user_confirmed=True)
        for other in (principal(app="niknolig-defense"), principal(subject="u2")):
            self.assertEqual(s.recall(other, "Lieblingsfarbe"), ())
            self.assertEqual(code(lambda: s.forget(other, record.id)), "NOT_FOUND")
            self.assertEqual(s.forget_all(other), 0)
        self.assertEqual(len(s.recall(a, "Lieblingsfarbe")), 1)

    def test_permissions_and_identity(self):
        s = service()
        self.assertEqual(code(lambda: s.remember(
            principal(perms=("memory:read",)), content="x y z", kind="fact",
            user_confirmed=True)), "AUTHORIZATION_DENIED")
        self.assertEqual(code(lambda: s.recall(principal(perms=()), "abc")),
                         "AUTHORIZATION_DENIED")
        for bad in (principal(active=False), principal(expires=999.0),
                    principal(expires=float("inf")), principal(expires=float("nan")),
                    principal(expires=10**10000), principal(app="other"),
                    principal(app=[]), principal(perms=("memory:read", 1)), None):
            self.assertEqual(code(lambda: s.recall(bad, "abc")), "AUTHENTICATION_INVALID")
        self.assertEqual(code(lambda: MemoryService(
            enabled=True, clock=lambda: -1).recall(principal(), "abc")),
            "AUTHENTICATION_INVALID")

    def test_rejects_credentials_and_oversize(self):
        s, p = service(), principal()
        for content in (
                "password: " + uuid4().hex,
                "password is " + uuid4().hex,
                "Bearer " + uuid4().hex,
                "api_key=" + uuid4().hex,
                "", "x" * 501, 5):
            self.assertEqual(code(lambda: s.remember(
                p, content=content, kind="fact", user_confirmed=True)),
                "VALIDATION_FAILED")
        self.assertEqual(code(lambda: s.remember(
            p, content="ok ok", kind="secret", user_confirmed=True)), "VALIDATION_FAILED")
        self.assertEqual(code(lambda: s.remember(
            p, content="ok ok", kind=[], user_confirmed=True)), "VALIDATION_FAILED")

    def test_retention_expiry(self):
        now = [1000.0]
        s = MemoryService(enabled=True, clock=lambda: now[0])
        p = principal(expires=10**9)
        s.remember(p, content="Termin Montag", kind="fact", user_confirmed=True,
                   retention_days=1)
        self.assertEqual(len(s.recall(p, "Termin")), 1)
        now[0] += 86401
        self.assertEqual(s.recall(p, "Termin"), ())

    def test_quota_and_erasure(self):
        s, p = service(), principal()
        for i in range(MAX_RECORDS_PER_PRINCIPAL):
            s.remember(p, content=f"note {i}", kind="fact", user_confirmed=True)
        self.assertEqual(code(lambda: s.remember(
            p, content="one more", kind="fact", user_confirmed=True)), "QUOTA_EXCEEDED")
        self.assertEqual(s.forget_all(p), MAX_RECORDS_PER_PRINCIPAL)

    def test_concurrent_writes_respect_per_principal_quota(self):
        s, p = service(), principal()

        def remember(index):
            try:
                return s.remember(
                    p, content=f"note number {index}", kind="fact",
                    user_confirmed=True,
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
                user_confirmed=True)
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
        if self.faults.get("put_after_write") == "raise":
            super().put(record, limit=limit)
            raise RuntimeError("secret-detail")
        if self.faults.get("put") == "raise":
            raise RuntimeError("secret-detail")
        if "put" in self.faults:
            return self.faults["put"]
        return super().put(record, limit=limit)

    def delete(self, app, subject, record_id):
        if self.faults.get("delete") == "raise":
            raise RuntimeError("secret-detail")
        if self.faults.get("delete") == "false":
            return False
        return super().delete(app, subject, record_id)

    def delete_all(self, app, subject):
        if self.faults.get("delete_all"):
            raise RuntimeError("secret-detail")
        return super().delete_all(app, subject)

    def list(self, app, subject):
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
                p, content="alpha beta", kind="fact", user_confirmed=True)),
                "STORE_UNAVAILABLE")
            self.assertEqual(store.list(p.app, p.subject), ())

        store = FaultyStore(put=False)
        s = MemoryService(store=store, enabled=True, clock=lambda: 1000.0)
        self.assertEqual(code(lambda: s.remember(
            p, content="alpha beta", kind="fact", user_confirmed=True)),
            "QUOTA_EXCEEDED")
        self.assertEqual(store.list(p.app, p.subject), ())

    def test_partial_write_failure_rolls_back_or_keeps_expiry_cleanup(self):
        p = principal()
        store = FaultyStore(put_after_write="raise", delete="raise")
        s = MemoryService(store=store, enabled=True, clock=lambda: 1000.0)
        self.assertEqual(code(lambda: s.remember(
            p, content="alpha beta", kind="fact", user_confirmed=True)),
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

    def test_expiry_scheduler_failure_prevents_write(self):
        store = InMemoryMemoryStore()
        s = MemoryService(store=store, enabled=True, clock=lambda: 1000.0)
        p = principal()
        with patch.object(_EXPIRY_SCHEDULER, "schedule",
                          side_effect=RuntimeError("scheduler unavailable")):
            self.assertEqual(code(lambda: s.remember(
                p, content="alpha beta", kind="fact", user_confirmed=True)),
                "STORE_UNAVAILABLE")
        self.assertEqual(store.list(p.app, p.subject), ())
        with patch("memory_engine.MAX_EXPIRY_JOBS", 0):
            self.assertEqual(code(lambda: s.remember(
                p, content="alpha beta", kind="fact", user_confirmed=True)),
                "STORE_UNAVAILABLE")
        self.assertEqual(store.list(p.app, p.subject), ())

    def test_total_memory_limit_and_deleted_state_are_bounded(self):
        store = InMemoryMemoryStore()
        s = MemoryService(store=store, enabled=True, clock=lambda: 1000.0)
        principals = [principal(subject=f"user-{i}") for i in range(3)]
        with patch("memory_engine.MAX_RECORDS_TOTAL", 2):
            records = [
                s.remember(p, content="alpha beta", kind="fact", user_confirmed=True)
                for p in principals[:2]
            ]
            self.assertEqual(code(lambda: s.remember(
                principals[2], content="alpha beta", kind="fact",
                user_confirmed=True)), "QUOTA_EXCEEDED")
            s.forget(principals[0], records[0].id)
            self.assertNotIn((principals[0].app, principals[0].subject), store._records)
            s.remember(
                principals[2], content="alpha beta", kind="fact", user_confirmed=True)
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
                p, content="alpha beta", kind="fact", user_confirmed=True)
            s.forget(p, record.id)
        self.assertEqual(store._records, {})
        with _EXPIRY_SCHEDULER._condition:
            self.assertFalse(any(
                entry[2]() is store for entry in _EXPIRY_SCHEDULER._queue))

    def test_update_requires_consent_and_valid_id(self):
        s, p = service(), principal()
        r = s.remember(p, content="alpha beta", kind="fact", user_confirmed=True)
        self.assertEqual(code(lambda: s.update(
            p, r.id, content="neu neu", user_confirmed=False)), "CONSENT_REQUIRED")
        for bad in (str(r.id), "../x", None, 1):
            self.assertEqual(code(lambda: s.update(
                p, bad, content="neu neu", user_confirmed=True)), "VALIDATION_FAILED")
            self.assertEqual(code(lambda: s.forget(p, bad)), "VALIDATION_FAILED")
        self.assertEqual(code(lambda: s.update(
            p, uuid4(), content="neu neu", user_confirmed=True)), "NOT_FOUND")
        self.assertEqual(s.recall(p, "alpha")[0].content, "alpha beta")

    def test_cross_app_cannot_update_or_delete(self):
        s = service()
        a, d = principal(), principal(app="niknolig-defense")
        r = s.remember(a, content="alpha beta", kind="fact", user_confirmed=True)
        self.assertEqual(code(lambda: s.update(
            d, r.id, content="x y z", user_confirmed=True)), "NOT_FOUND")
        self.assertEqual(code(lambda: s.forget(d, r.id)), "NOT_FOUND")
        self.assertEqual(s.recall(a, "alpha")[0].content, "alpha beta")

    def test_expired_records_are_physically_removed(self):
        now = [1000.0]
        store = InMemoryMemoryStore()
        s = MemoryService(store=store, enabled=True, clock=lambda: now[0])
        p = principal(expires=10**9)
        s.remember(p, content="alpha beta", kind="fact", user_confirmed=True,
                   retention_days=1)
        now[0] += 86401
        s.recall(p, "alpha")
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
                                user_confirmed=True, retention_days=1)
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
                             user_confirmed=True, retention_days=1)
        now[0] += 86401
        current = s.remember(p, content="current note", kind="fact",
                             user_confirmed=True, retention_days=1)
        s.forget(p, current.id)
        self.assertIsNone(store.get(p.app, p.subject, expired.id))
        self.assertEqual(store.list(p.app, p.subject), ())

    def test_deletion_failures_are_not_reported_as_success(self):
        for fault in ("raise", "false"):
            store = FaultyStore()
            s = MemoryService(store=store, enabled=True, clock=lambda: 1000.0)
            p = principal()
            r = s.remember(p, content="alpha beta", kind="fact", user_confirmed=True)
            store.faults["delete"] = fault
            self.assertIn(code(lambda: s.forget(p, r.id)),
                          ("STORE_UNAVAILABLE", "NOT_FOUND"))
            self.assertEqual(len(store.list(p.app, p.subject)), 1)
        store.faults = {"delete_all": True}
        self.assertEqual(code(lambda: s.forget_all(p)), "STORE_UNAVAILABLE")

    def test_expired_purge_failure_fails_closed_without_leaking(self):
        now = [1000.0]
        store = FaultyStore()
        s = MemoryService(store=store, enabled=True, clock=lambda: now[0])
        p = principal(expires=10**9)
        s.remember(p, content="alpha beta", kind="fact", user_confirmed=True,
                   retention_days=1)
        now[0] += 86401
        store.faults["delete"] = "raise"
        with self.assertRaises(MemoryEngineError) as ctx:
            s.recall(p, "alpha")
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
                            user_confirmed=True, retention_days=1)
        now[0] += 86401
        store.block_expiry_list = True
        with ThreadPoolExecutor(max_workers=1) as pool:
            recall = pool.submit(s.recall, p, "alpha")
            self.assertTrue(store.expired_listed.wait(1))
            self.assertTrue(store.delete(p.app, p.subject, record.id))
            store.finish_list.set()
            self.assertEqual(recall.result(timeout=2), ())
        self.assertEqual(store.list(p.app, p.subject), ())

    def test_foreign_records_from_faulty_store_are_ignored(self):
        store = FaultyStore()
        s = MemoryService(store=store, enabled=True, clock=lambda: 1000.0)
        s.remember(principal(app="niknolig-defense"), content="alpha beta",
                   kind="fact", user_confirmed=True)
        store.faults["foreign"] = True
        self.assertEqual(s.recall(principal(), "alpha"), ())


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

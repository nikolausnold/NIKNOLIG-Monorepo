from pathlib import Path
import sys
import unittest
from uuid import uuid4


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_support import Principal
from memory_engine import (
    InMemoryMemoryStore, MAX_RECORDS_PER_PRINCIPAL, MemoryEngineError, MemoryService,
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
                    principal(app="other"), None):
            self.assertEqual(code(lambda: s.recall(bad, "abc")), "AUTHENTICATION_INVALID")

    def test_rejects_credentials_and_oversize(self):
        s, p = service(), principal()
        for content in ("password: " + uuid4().hex, "", "x" * 501, 5):
            self.assertEqual(code(lambda: s.remember(
                p, content=content, kind="fact", user_confirmed=True)),
                "VALIDATION_FAILED")
        self.assertEqual(code(lambda: s.remember(
            p, content="ok ok", kind="secret", user_confirmed=True)), "VALIDATION_FAILED")

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


class FaultyStore(InMemoryMemoryStore):
    def __init__(self, **faults):
        super().__init__()
        self.faults = faults

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

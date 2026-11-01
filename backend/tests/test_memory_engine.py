from pathlib import Path
import sys
import unittest
from uuid import uuid4


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_support import Principal
from memory_engine import MAX_RECORDS_PER_PRINCIPAL, MemoryError_, MemoryService


def principal(app="niknolig", subject="u1", perms=("memory:read", "memory:write"),
              active=True, expires=2000.0):
    return Principal(subject, app, frozenset(perms), expires, active)


def service(enabled=True):
    return MemoryService(enabled=enabled, clock=lambda: 1000.0)


def code(callable_):
    try:
        callable_()
    except MemoryError_ as exc:
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


if __name__ == "__main__":
    unittest.main()

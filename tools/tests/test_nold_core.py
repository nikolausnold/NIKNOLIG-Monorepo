import copy
import json
import unittest
from pathlib import Path

from tools.nold_core import (
    CoreInputError,
    KnowledgeLedger,
    evaluate_fixture,
    validate_entry,
)


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "nold-core-v1.json"


class NoldCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_versioned_sandbox_fixtures_pass(self):
        report = evaluate_fixture(self.fixture)
        self.assertTrue(report["passed"])
        self.assertEqual(1, report["schemaVersion"])
        self.assertFalse(report["networkAccess"])
        self.assertFalse(report["fixtureCodeExecuted"])
        self.assertEqual(8, len(report["results"]))

    def test_report_does_not_echo_claims_or_sources(self):
        report = evaluate_fixture(self.fixture)
        encoded = json.dumps(report)
        self.assertNotIn("A health endpoint", encoded)
        self.assertNotIn("backend/tests/test_server.py", encoded)

    def test_fact_requires_a_source_and_nonzero_confidence(self):
        for confidence in (0, 0.5):
            record = {
                "kind": "fact",
                "claim": "A bounded claim.",
                "sources": [],
                "recordedAt": "2026-10-16T21:00:00Z",
                "confidence": confidence,
            }
            with self.subTest(confidence=confidence), self.assertRaisesRegex(
                CoreInputError, "fact_requires_source_and_confidence"
            ):
                validate_entry(record)

    def test_ledger_is_append_only_and_enforces_capacity(self):
        ledger = KnowledgeLedger(capacity=1)
        entry = ledger.append(self.fixture["cases"][0]["record"])
        self.assertEqual((entry,), ledger.entries)
        with self.assertRaisesRegex(CoreInputError, "ledger_capacity_reached"):
            ledger.append(self.fixture["cases"][2]["record"])
        with self.assertRaises(CoreInputError):
            KnowledgeLedger(capacity=0)

    def test_ledger_stores_canonical_timestamp_with_bounded_fraction(self):
        record = {
            "kind": "assumption",
            "claim": "A bounded claim.",
            "sources": [],
            "recordedAt": "2026-10-16T21:00:00." + "1" * 1_000 + "Z",
            "confidence": 0.2,
        }
        entry = KnowledgeLedger().append(record)
        self.assertEqual("2026-10-16T21:00:00.111111+00:00", entry.recorded_at)

    def test_unknown_cannot_smuggle_evidence_or_confidence(self):
        record = {
            "kind": "unknown",
            "claim": "The value remains unknown.",
            "sources": [],
            "recordedAt": "2026-10-16T21:00:00Z",
            "confidence": 0.1,
        }
        with self.assertRaisesRegex(CoreInputError, "unknown_must_not_claim_evidence"):
            validate_entry(record)

    def test_secret_like_content_is_rejected_without_echoing_it(self):
        record = {
            "kind": "assumption",
            "claim": "token=not-for-logs",
            "sources": [],
            "recordedAt": "2026-10-16T21:00:00Z",
            "confidence": 0.2,
        }
        with self.assertRaisesRegex(CoreInputError, "sensitive_text_rejected") as raised:
            validate_entry(record)
        self.assertNotIn("not-for-logs", str(raised.exception))

    def test_invalid_case_fixture_is_rejected(self):
        for fixture in (
            {},
            {"schemaVersion": True, "cases": []},
            {"schemaVersion": 2, "cases": []},
            {"schemaVersion": 1, "cases": []},
        ):
            with self.subTest(fixture=fixture), self.assertRaises(CoreInputError):
                evaluate_fixture(fixture)

    def test_duplicate_case_ids_are_rejected(self):
        fixture = copy.deepcopy(self.fixture)
        fixture["cases"][1]["id"] = fixture["cases"][0]["id"]
        with self.assertRaisesRegex(CoreInputError, "invalid_case_id"):
            evaluate_fixture(fixture)

    def test_fixture_claim_does_not_execute_code(self):
        fixture = copy.deepcopy(self.fixture)
        fixture["cases"][0]["record"]["claim"] = "__import__('os').system('false')"
        report = evaluate_fixture(fixture)
        self.assertTrue(report["results"][0]["passed"])
        self.assertFalse(report["fixtureCodeExecuted"])


if __name__ == "__main__":
    unittest.main()

import copy
import json
import unittest
from pathlib import Path

from tools.evolution_engine import (
    BacklogError,
    build_report,
    classify,
    priority_score,
    validate_backlog,
)


ROOT = Path(__file__).resolve().parents[2]
BACKLOG_PATH = ROOT / "evolution" / "ideas.json"


class EvolutionEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.backlog = json.loads(BACKLOG_PATH.read_text(encoding="utf-8"))

    def test_curated_backlog_is_evidence_checked_and_ranked(self):
        ideas = validate_backlog(self.backlog, ROOT)
        report = build_report(ideas)
        self.assertEqual(1, report["cycle"]["runs"])
        self.assertFalse(report["cycle"]["repeatAutomatically"])
        self.assertEqual(
            sorted(report["ideas"], key=lambda item: (-item["score"], item["id"])),
            report["ideas"],
        )
        self.assertEqual(
            {"repositoryWrites": False, "commandsRun": False, "networkAccess": False,
             "deployments": False, "secretsRead": False, "appOrSensorRuntimeChanged": False},
            report["execution"],
        )
        self.assertTrue(any(idea["tier"] == "AUTO" for idea in report["ideas"]))
        self.assertTrue(any(idea["tier"] == "VORSCHLAG" for idea in report["ideas"]))
        self.assertTrue(any(idea["tier"] == "GESPERRT" for idea in report["ideas"]))

    def test_risk_flags_override_high_benefit_and_auth_changes_are_locked(self):
        ideas = validate_backlog(self.backlog, ROOT)
        blocked = next(idea for idea in ideas if idea["id"] == "device-session-transfer")
        self.assertEqual("GESPERRT", classify(blocked)[0])
        self.assertIn("authentication", classify(blocked)[1])
        self.assertEqual(-6, priority_score({"impact": 5, "effort": 5, "risk": 5, "feasibility": 2}))

    def test_stale_or_changed_citation_is_rejected(self):
        modified = copy.deepcopy(self.backlog)
        modified["ideas"][0]["evidence"][0]["excerpt"] = "invented repository finding"
        with self.assertRaisesRegex(BacklogError, "does not match cited lines"):
            validate_backlog(modified, ROOT)

    def test_existing_excerpt_outside_cited_line_range_is_rejected(self):
        modified = copy.deepcopy(self.backlog)
        citation = modified["ideas"][0]["evidence"][0]
        source = (ROOT / citation["path"]).read_text(encoding="utf-8")
        self.assertIn(citation["excerpt"], source)
        citation["startLine"] = 1
        citation["endLine"] = 1
        with self.assertRaisesRegex(BacklogError, "does not match cited lines"):
            validate_backlog(modified, ROOT)

    def test_private_or_external_evidence_paths_are_rejected(self):
        for path in ("/etc/passwd", "../outside.md", "backend/.env"):
            modified = copy.deepcopy(self.backlog)
            modified["ideas"][0]["evidence"][0]["path"] = path
            with self.subTest(path=path), self.assertRaises(BacklogError):
                validate_backlog(modified, ROOT)

    def test_invalid_limits_and_duplicate_ids_are_rejected(self):
        ideas = validate_backlog(self.backlog, ROOT)
        for limit in (0, 21):
            with self.subTest(limit=limit), self.assertRaises(BacklogError):
                build_report(ideas, limit)
        modified = copy.deepcopy(self.backlog)
        modified["ideas"][1]["id"] = modified["ideas"][0]["id"]
        with self.assertRaisesRegex(BacklogError, "duplicate idea id"):
            validate_backlog(modified, ROOT)

    def test_security_like_text_is_never_reported(self):
        modified = copy.deepcopy(self.backlog)
        modified["ideas"][0]["rationale"] = "api_key=super-secret-value"
        with self.assertRaisesRegex(BacklogError, "secret-like text"):
            validate_backlog(modified, ROOT)

    def test_malformed_untrusted_flags_fail_with_backlog_error(self):
        modified = copy.deepcopy(self.backlog)
        modified["ideas"][0]["riskFlags"] = [{}]
        with self.assertRaisesRegex(BacklogError, "risk flags must be strings"):
            validate_backlog(modified, ROOT)

    def test_cycle_rejects_backlog_larger_than_hard_cap(self):
        modified = copy.deepcopy(self.backlog)
        modified["ideas"] *= 6
        with self.assertRaisesRegex(BacklogError, "cycle limit"):
            validate_backlog(modified, ROOT)

    def test_evidence_states_do_not_promote_hypotheses_to_facts(self):
        ideas = validate_backlog(self.backlog, ROOT)
        auto_idea = next(idea for idea in ideas if idea["id"] == "accessibility-preview-checklist")
        report = build_report([auto_idea])
        self.assertEqual("Hypothese", report["ideas"][0]["evidenceConfidence"])


if __name__ == "__main__":
    unittest.main()

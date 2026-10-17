import copy
import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import mock_open, patch

from tools.source_readiness import CHECKS, DEFAULT_REGISTRY, assess_sources, main


class SourceReadinessTests(unittest.TestCase):
    def setUp(self):
        self.registry = json.loads(DEFAULT_REGISTRY.read_text(encoding="utf-8"))

    def test_candidates_are_blocked_and_cover_requested_source_types(self):
        report = assess_sources(self.registry)
        self.assertEqual(
            {"traffic", "camera", "airspace", "weather", "internet", "local_sensor"},
            {source["category"] for source in report["sources"]},
        )
        self.assertFalse(report["evidence_verified"])
        self.assertFalse(report["release_authorized"])
        for source in report["sources"]:
            self.assertEqual("blocked", source["status"])
            self.assertEqual(list(CHECKS), source["blockers"])
            self.assertFalse(source["access_enabled"])

    def test_documented_claims_never_authorize_access_or_release(self):
        for source in self.registry["sources"]:
            source["checks"] = dict.fromkeys(CHECKS, "documented")
        report = assess_sources(self.registry)
        for source in report["sources"]:
            self.assertEqual("independent_review_required", source["status"])
            self.assertFalse(source["access_enabled"])
        self.assertFalse(report["release_authorized"])
        self.assertFalse(report["evidence_verified"])
        for check in CHECKS:
            data = copy.deepcopy(self.registry)
            data["sources"][0]["checks"][check] = "pending"
            with self.subTest(check=check):
                self.assertEqual([check], assess_sources(data)["sources"][0]["blockers"])

    def test_rejects_unknown_missing_duplicate_or_mistyped_values(self):
        mutations = [
            lambda data: data.update(version=True),
            lambda data: data.update(sources=[]),
            lambda data: data.update(sources=data["sources"] * 4),
            lambda data: data["sources"].append(copy.deepcopy(data["sources"][0])),
            lambda data: data["sources"][0].update(id="../camera"),
            lambda data: data["sources"][0].update(category="unrestricted"),
            lambda data: data["sources"][0].update(endpoint="https://example.invalid"),
            lambda data: data["sources"][0]["checks"].pop(CHECKS[0]),
            lambda data: data["sources"][0]["checks"].update(extra="documented"),
        ]
        for value in (True, None, [], {}, 1, "approved"):
            mutations.append(
                lambda data, value=value: data["sources"][0]["checks"].update(
                    access_and_license=value
                )
            )
        for mutation in mutations:
            data = copy.deepcopy(self.registry)
            mutation(data)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                assess_sources(data)

    def test_cli_blocked_review_and_invalid_exit_codes(self):
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(1, main([]))
        self.assertEqual("offline_prerequisite_assessment", json.loads(output.getvalue())["mode"])
        for source in self.registry["sources"]:
            source["checks"] = dict.fromkeys(CHECKS, "documented")
        with patch("tools.source_readiness.Path.open",
                   mock_open(read_data=json.dumps(self.registry).encode())), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(0, main([]))
        for content in (
            b'{"version":1,"version":1,"sources":[]}',
            b"invalid sensitive input",
            b"x" * 64_001,
            b"\xff",
        ):
            with patch("tools.source_readiness.Path.open", mock_open(read_data=content)), \
                    redirect_stdout(io.StringIO()) as output:
                self.assertEqual(2, main([]))
            self.assertEqual("invalid_input", json.loads(output.getvalue())["status"])
            self.assertNotIn("sensitive", output.getvalue())
        with patch("tools.source_readiness.Path.open", side_effect=OSError), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(2, main([]))


if __name__ == "__main__":
    unittest.main()

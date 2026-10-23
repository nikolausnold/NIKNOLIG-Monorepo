import copy
import io
import json
import os
import unittest
import urllib.error
from contextlib import redirect_stdout
from unittest.mock import MagicMock, patch

from tools.system_updates import (
    DEFAULT_REGISTRY,
    GitHubReader,
    InventoryError,
    NoRedirect,
    build_report,
    main,
    validate_registry,
)


HEAD = "a" * 40
LOCAL = "b" * 40


class SystemUpdatesTests(unittest.TestCase):
    def setUp(self):
        self.registry = json.loads(DEFAULT_REGISTRY.read_text(encoding="utf-8"))
        self.entries = validate_registry(self.registry)

    def test_curated_registry_has_known_sources_and_onboarded_ios(self):
        self.assertTrue(DEFAULT_REGISTRY.is_absolute())
        sources = {entry["id"]: entry for entry in self.entries}
        self.assertEqual("nikolausnold/NIKNOLIG-Monorepo", sources["monorepo"]["repository"])
        self.assertEqual("nikolausnold/NIKNOLIG-Defense-Website-", sources["niknolig-defense"]["repository"])
        self.assertEqual("3c4d6618a61604f6433639151e741371491a5f0d", sources["niknolig"]["baseline"])
        self.assertEqual("nikolausnold/NIKNOLIG-Defense-Website-", sources["niknolig-defense"]["repository"])
        self.assertEqual("5f0f385089bc27347eacd282c13a546eb4511da2", sources["niknolig-defense"]["baseline"])
        self.assertEqual("external", sources["ios"]["kind"])
        self.assertEqual(
            "nikolausnold/nikolausnold-NIKNOLIG-iOS-Monorepo",
            sources["ios"]["repository"],
        )
        self.assertEqual(
            "afe4f5a3f0b84500437484a3bf0b3976d7b99e58",
            sources["ios"]["baseline"],
        )

    def test_registry_rejects_untrusted_paths_and_malformed_baselines(self):
        for repository in (
            "other/repo", "https://evil.example/repo", "nikolausnold/../repo",
            "nikolausnold/..", "nikolausnold/repo?token=x", "nikolausnold/repo#x",
            "nikolausnold/repo\n", "nikolausnold/repo/extra", None, [],
        ):
            data = copy.deepcopy(self.registry)
            data["repositories"][1]["repository"] = repository
            with self.subTest(repository=repository), self.assertRaises(InventoryError):
                validate_registry(data)
        for baseline in (None, "", "1234", "g" * 40, "a" * 40 + "\n", 42, []):
            data = copy.deepcopy(self.registry)
            data["repositories"][1]["baseline"] = baseline
            with self.subTest(baseline=baseline), self.assertRaises(InventoryError):
                validate_registry(data)

    def test_registry_fails_closed_on_duplicates_unknown_keys_and_missing_local(self):
        mutations = [
            lambda data: data["repositories"].append(copy.deepcopy(data["repositories"][1])),
            lambda data: data["repositories"][2].update(repository="nikolausnold/niknolig"),
            lambda data: data["repositories"][1].update(command="do not execute"),
            lambda data: data.update(version=True),
            lambda data: data.update(repositories=[]),
            lambda data: data["repositories"].pop(0),
            lambda data: data["repositories"][0].update(repository="nikolausnold/other"),
            lambda data: data["repositories"][3].update(baseline="not-a-sha"),
            lambda data: data["repositories"][1].update(kind="automatic"),
        ]
        for mutation in mutations:
            data = copy.deepcopy(self.registry)
            mutation(data)
            with self.subTest(mutation=mutation), self.assertRaises(InventoryError):
                validate_registry(data)

    def test_future_repository_requires_explicit_baseline_onboarding(self):
        self.registry["repositories"].append({
            "id": "future-app", "kind": "external",
            "repository": "nikolausnold/Future-App", "baseline": HEAD,
        })
        self.assertEqual(5, len(validate_registry(self.registry)))

    def test_report_compares_external_repositories_including_ios(self):
        reader = MagicMock()
        niknolig_baseline = self.entries[1]["baseline"]
        ios_baseline = self.entries[3]["baseline"]
        reader.head.side_effect = [
            ("main", HEAD),
            ("release", niknolig_baseline),
            ("main", HEAD),
            ("main", ios_baseline),
        ]
        report = build_report(self.entries, reader, LOCAL)
        local, unchanged, changed, ios = report["repositories"]
        self.assertTrue(report["all_configured_repositories_checked"])
        self.assertEqual([], report["pending_configuration"])
        self.assertEqual(LOCAL, local["local_build_sha"])
        self.assertEqual(HEAD, local["observed_sha"])
        self.assertIsNone(local["changed"])
        self.assertFalse(unchanged["changed"])
        self.assertTrue(changed["changed"])
        self.assertIn("no update adopted", report["semantics"]["changed"])
        self.assertEqual("checked", ios["status"])
        self.assertFalse(ios["changed"])
        self.assertEqual(4, reader.head.call_count)

    def test_failure_does_not_skip_remaining_repositories_or_claim_unchanged(self):
        reader = MagicMock()
        reader.head.side_effect = [
            InventoryError("GitHub HTTP 404"),
            ("main", HEAD),
            ("main", HEAD),
            ("main", HEAD),
        ]
        report = build_report(self.entries, reader)
        self.assertFalse(report["all_configured_repositories_checked"])
        self.assertEqual(4, len(report["repositories"]))
        self.assertEqual("not_checked", report["repositories"][0]["status"])
        self.assertIsNone(report["repositories"][0]["changed"])
        self.assertEqual("not_available", report["repositories"][0]["local_reference_status"])
        self.assertEqual("checked", report["repositories"][2]["status"])

    def test_invalid_local_sha_fails_before_network(self):
        reader = MagicMock()
        for sha in ("", "branch-name", HEAD + "\n"):
            with self.subTest(sha=sha), self.assertRaises(InventoryError):
                build_report(self.entries, reader, sha)
        reader.head.assert_not_called()

    def test_api_uses_fixed_origin_get_and_encoded_default_branch(self):
        reader = GitHubReader("test-token")
        reader.opener = MagicMock()
        responses = [{"default_branch": "release/mobile", "url": "https://evil.example"},
                     {"sha": HEAD}]
        reader.opener.open.return_value.__enter__.return_value.read.side_effect = [
            json.dumps(response).encode() for response in responses
        ]
        self.assertEqual(("release/mobile", HEAD), reader.head("nikolausnold/NIKNOLIG"))
        calls = reader.opener.open.call_args_list
        self.assertEqual(
            ["https://api.github.com/repos/nikolausnold/NIKNOLIG",
             "https://api.github.com/repos/nikolausnold/NIKNOLIG/commits/release%2Fmobile"],
            [call.args[0].full_url for call in calls],
        )
        for call in calls:
            self.assertEqual("GET", call.args[0].get_method())
            self.assertEqual("Bearer " + reader.token, call.args[0].get_header("Authorization"))
            self.assertEqual(20, call.kwargs["timeout"])

    def test_redirects_are_disabled_and_errors_do_not_echo_credentials(self):
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, "", {}, "https://evil.example"))
        reader = GitHubReader("test-token")
        self.assertTrue(any(isinstance(handler, NoRedirect) for handler in reader.opener.handlers))
        reader.opener = MagicMock()
        for error in (
            urllib.error.HTTPError("https://evil.example/test-token", 302, "test-token", {}, None),
            urllib.error.HTTPError("https://api.github.com", 403, "test-token", {}, None),
            urllib.error.HTTPError("https://api.github.com", 404, "test-token", {}, None),
            urllib.error.URLError("test-token"),
            TimeoutError("test-token"),
        ):
            reader.opener.open.side_effect = error
            with self.subTest(error=error), self.assertRaises(InventoryError) as caught:
                reader.head("nikolausnold/NIKNOLIG")
            self.assertNotIn("test-token", str(caught.exception))

    def test_api_rejects_bad_payloads_and_unsafe_repository_before_request(self):
        reader = GitHubReader()
        reader.opener = MagicMock()
        for payload in (b"not json", b"[]", b"x" * 1_000_001):
            reader.opener.open.return_value.__enter__.return_value.read.return_value = payload
            with self.subTest(payload=payload[:10]), self.assertRaises(InventoryError):
                reader.head("nikolausnold/NIKNOLIG")
        reader.opener.reset_mock()
        with self.assertRaises(InventoryError):
            reader.head("https://evil.example")
        reader.opener.open.assert_not_called()
        for metadata in ({}, {"default_branch": None}, {"default_branch": "\n"}):
            with patch.object(reader, "get", return_value=metadata), self.assertRaises(InventoryError):
                reader.head("nikolausnold/NIKNOLIG")
        with patch.object(reader, "get", side_effect=[{"default_branch": "main"}, {"sha": "invalid"}]):
            with self.assertRaises(InventoryError):
                reader.head("nikolausnold/NIKNOLIG")

    def run_cli(self, side_effect, arguments=None):
        output = io.StringIO()
        with patch.dict(os.environ, {"GITHUB_SHA": LOCAL}, clear=True), \
                patch("tools.system_updates.GitHubReader.head", side_effect=side_effect), \
                redirect_stdout(output):
            exit_code = main(arguments or [])
        return exit_code, output.getvalue()

    def test_cli_emits_complete_json_and_failure_exit_code(self):
        code, output = self.run_cli([
            ("main", HEAD),
            InventoryError("unavailable"),
            ("main", HEAD),
            ("main", HEAD),
        ])
        self.assertEqual(1, code)
        report = json.loads(output)
        self.assertEqual(4, len(report["repositories"]))
        self.assertEqual("not_checked", report["repositories"][1]["status"])
        code, output = self.run_cli([("main", HEAD)] * 4)
        self.assertEqual(0, code)
        self.assertEqual([], json.loads(output)["pending_configuration"])

    def test_cli_output_file_and_unwritable_output_fallback(self):
        with patch("tools.system_updates.Path.write_text") as write:
            code, output = self.run_cli([("main", HEAD)] * 4, ["--output", "inventory.json"])
            self.assertEqual(0, code)
            self.assertEqual("", output)
            self.assertEqual(4, len(json.loads(write.call_args.args[0])["repositories"]))
        with patch("tools.system_updates.Path.write_text", side_effect=PermissionError):
            code, output = self.run_cli([("main", HEAD)] * 4, ["--output", "inventory.json"])
            self.assertEqual(2, code)
            self.assertTrue(json.loads(output)["all_configured_repositories_checked"])

    def test_invalid_registry_emits_failure_without_network(self):
        for content in ('{"version":1,"version":1,"repositories":[]}', "not JSON", "{}"):
            with patch("tools.system_updates.Path.read_text", return_value=content), \
                    patch("tools.system_updates.GitHubReader.head") as head, \
                    redirect_stdout(io.StringIO()) as output:
                self.assertEqual(2, main([]))
            head.assert_not_called()
            self.assertEqual("invalid_input", json.loads(output.getvalue())["status"])


if __name__ == "__main__":
    unittest.main()

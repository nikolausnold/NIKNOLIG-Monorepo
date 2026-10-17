import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class AutobuildTests(unittest.TestCase):
    def test_audit_uses_only_local_checkout_without_secrets(self):
        workflow = (ROOT / ".github/workflows/audit-workers.yml").read_text()
        for guard in (
            "contents: read",
            "uses: actions/checkout@",
            "persist-credentials: false",
            'python3 - "$GITHUB_WORKSPACE" "$GITHUB_STEP_SUMMARY"',
        ):
            with self.subTest(guard=guard):
                self.assertIn(guard, workflow)
        self.assertNotIn("secrets.", workflow)
        self.assertNotIn("WORKERS_REPOSITORY_URL", workflow)
        self.assertNotIn("WORKERS_REPO_READ_PAT", workflow)
        self.assertNotIn("git clone", workflow)

    def test_audit_runs_without_valid_legacy_configuration(self):
        workflow = (ROOT / ".github/workflows/audit-workers.yml").read_text()
        script = textwrap.dedent(workflow.split("        run: |\n", 1)[1])
        for legacy_value in (None, "not-a-github-clone-url"):
            with self.subTest(legacy_value=legacy_value), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / "README.md").write_text("# Local audit fixture\n")
                summary = root / "summary.txt"
                env = os.environ.copy()
                for name in ("WORKERS_REPOSITORY_URL", "WORKERS_REPO_READ_PAT"):
                    env.pop(name, None)
                    if legacy_value is not None:
                        env[name] = legacy_value
                env.update(GITHUB_WORKSPACE=str(root), GITHUB_STEP_SUMMARY=str(summary))
                result = subprocess.run(
                    ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", script],
                    cwd=root,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                report = summary.read_text()
                self.assertIn("- Files inspected: 1", report)
                self.assertIn("# Local audit fixture", report)
                self.assertIn("This report inspects this repository only.", report)
                self.assertNotIn("not-a-github-clone-url", report)

    def test_release_only_signs_successful_trusted_main_build_commit(self):
        workflow = (ROOT / ".github/workflows/android-release.yml").read_text()
        for guard in (
            "workflows: [\"Android apps build\"]",
            "github.event.workflow_run.conclusion == 'success'",
            "github.event.workflow_run.head_repository.full_name == github.repository",
            "github.event.workflow_run.head_branch == 'main'",
            'fromJSON(\'["push", "schedule", "workflow_dispatch"]\')',
            "ref: ${{ github.event.workflow_run.head_sha || github.sha }}",
            "environment: android-release",
            "persist-credentials: false",
            "1000 + GITHUB_RUN_NUMBER",
        ):
            with self.subTest(guard=guard):
                self.assertIn(guard, workflow)
        self.assertNotIn("pull_request_target", workflow)

    def test_both_apps_keep_local_versions_and_validate_update_versions(self):
        for app in ("niknolig", "niknolig-defense"):
            build = (ROOT / "apps" / app / "build.gradle.kts").read_text()
            with self.subTest(app=app):
                self.assertIn('environmentVariable("NIKNOLIG_VERSION_CODE")', build)
                self.assertIn("requireNotNull(it.toIntOrNull())", build)
                self.assertIn("require(code in 2..2100000000)", build)
                self.assertIn("versionCode = updateVersionCode ?: 1", build)
                self.assertIn('versionName = updateVersionCode?.let { "0.1.$it" } ?: "0.1.0"', build)

    def test_autobuild_checks_tools_and_exports_shared_contracts(self):
        workflow = (ROOT / ".github/workflows/android-build.yml").read_text()
        for check in (
            'cron: "23 4 * * 1"',
            "python3 -m unittest discover -s backend/tests",
            "python3 -m unittest discover -s tools/tests",
            "python3 -m tools.system_updates --output",
            "github.ref == 'refs/heads/main' && github.event_name != 'pull_request'",
            "mobile-contracts-${{ github.sha }}",
            "backend/openapi.yaml",
            "backend/contracts/*.json",
            "config/system-repositories.json",
        ):
            with self.subTest(check=check):
                self.assertIn(check, workflow)


if __name__ == "__main__":
    unittest.main()

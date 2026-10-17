import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/audit-workers.yml"


class AuditWorkersTests(unittest.TestCase):
    def test_audit_uses_read_only_local_checkout_without_external_secrets(self):
        workflow = WORKFLOW.read_text()
        for setting in (
            "contents: read",
            "uses: actions/checkout@",
            "persist-credentials: false",
            'python3 - "$GITHUB_WORKSPACE" "$GITHUB_STEP_SUMMARY"',
        ):
            with self.subTest(setting=setting):
                self.assertIn(setting, workflow)
        self.assertNotIn("secrets.", workflow)
        self.assertNotIn("WORKERS_REPOSITORY_URL", workflow)
        self.assertNotIn("WORKERS_REPO_READ_PAT", workflow)

    @unittest.skipUnless(shutil.which("bash"), "bash is required for audit tests")
    def test_audit_produces_summary_without_valid_external_configuration(self):
        script = textwrap.dedent(WORKFLOW.read_text().split("        run: |\n", 1)[1])
        with tempfile.TemporaryDirectory(prefix="niknolig-audit-test-") as directory:
            root = Path(directory) / "repository"
            root.mkdir()
            (root / "README.md").write_text("# Local audit fixture\n", encoding="utf-8")
            workflows = root / ".github/workflows"
            workflows.mkdir(parents=True)
            (workflows / "fixture.yml").write_text("name: Fixture\n", encoding="utf-8")
            summary = Path(directory) / "summary.md"
            environment = dict(
                os.environ,
                GITHUB_WORKSPACE=str(root),
                GITHUB_STEP_SUMMARY=str(summary),
            )
            environment.pop("WORKERS_REPOSITORY_URL", None)
            environment.pop("WORKERS_REPO_READ_PAT", None)
            for external_url in (None, "not-a-github-clone-url"):
                with self.subTest(external_url=external_url):
                    if external_url is not None:
                        environment["WORKERS_REPOSITORY_URL"] = external_url
                    summary.write_text("", encoding="utf-8")
                    result = subprocess.run(
                        ["bash", "-e", "-o", "pipefail", "-c", script],
                        cwd=directory, env=environment, capture_output=True,
                        text=True, timeout=15,
                    )
                    self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                    report = summary.read_text(encoding="utf-8")
                    for expected in (
                        "# Read-only repository audit",
                        "- Files inspected: 2",
                        "- README files: 1",
                        "- Workflow files: 1",
                        "- `README.md`: # Local audit fixture",
                        "- `.github/workflows/fixture.yml`",
                    ):
                        self.assertIn(expected, report)


if __name__ == "__main__":
    unittest.main()

import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/audit-workers.yml"


class AuditWorkersTests(unittest.TestCase):
    def test_workflow_uses_read_only_local_checkout_without_legacy_secrets(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("  contents: read\n", workflow)
        self.assertIn("uses: actions/checkout@", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertNotIn("secrets.", workflow)
        self.assertNotIn("WORKERS_REPOSITORY_URL", workflow)
        self.assertNotIn("WORKERS_REPO_READ_PAT", workflow)
        self.assertNotIn("git clone", workflow)

    def test_audit_runs_with_missing_or_invalid_legacy_configuration(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        _, separator, body = workflow.partition("        run: |\n")
        self.assertTrue(separator, "Audit run step must exist")
        script = textwrap.dedent(body)
        for legacy_url in (None, "not-a-credential-free-https-clone-url"):
            with self.subTest(legacy_url=legacy_url), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "repository"
                root.mkdir()
                (root / "README.md").write_text("# Local audit fixture\n", encoding="utf-8")
                workflows = root / ".github/workflows"
                workflows.mkdir(parents=True)
                (workflows / "fixture.yml").write_text("name: Fixture\n", encoding="utf-8")
                summary = Path(tmp) / "summary.md"
                env = os.environ.copy()
                for name in ("WORKERS_REPOSITORY_URL", "WORKERS_REPO_READ_PAT"):
                    env.pop(name, None)
                if legacy_url is not None:
                    env["WORKERS_REPOSITORY_URL"] = legacy_url
                    env["WORKERS_REPO_READ_PAT"] = "unused-legacy-value"
                env.update(GITHUB_WORKSPACE=str(root), GITHUB_STEP_SUMMARY=str(summary))
                result = subprocess.run(
                    ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", script],
                    cwd=tmp,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertEqual(0, result.returncode, result.stderr)
                report = summary.read_text(encoding="utf-8")
                self.assertIn("- Files inspected: 2", report)
                self.assertIn("- README files: 1", report)
                self.assertIn("- Workflow files: 1", report)
                self.assertIn("# Local audit fixture", report)
                self.assertIn("`.github/workflows/fixture.yml`", report)
                self.assertIn("This report inspects this repository only.", report)
                self.assertNotIn("unused-legacy-value", report)
                if legacy_url is not None:
                    self.assertNotIn(legacy_url, report)


if __name__ == "__main__":
    unittest.main()

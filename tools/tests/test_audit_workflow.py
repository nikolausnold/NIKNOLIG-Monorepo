import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/audit-workers.yml"


class AuditWorkflowTests(unittest.TestCase):
    def test_audit_uses_read_only_local_checkout_without_external_secrets(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        for guard in (
            "contents: read",
            "uses: actions/checkout@",
            "persist-credentials: false",
            'python3 - "$GITHUB_WORKSPACE" "$GITHUB_STEP_SUMMARY"',
        ):
            with self.subTest(guard=guard):
                self.assertIn(guard, workflow)
        for external_dependency in (
            "secrets.",
            "WORKERS_REPOSITORY_URL",
            "WORKERS_REPO_READ_PAT",
            "git clone",
            "GIT_ASKPASS",
        ):
            with self.subTest(external_dependency=external_dependency):
                self.assertNotIn(external_dependency, workflow)

    def test_audit_generates_summary_without_secrets_or_valid_external_url(self):
        script = textwrap.dedent(
            WORKFLOW.read_text(encoding="utf-8").split("        run: |\n", 1)[1]
        )
        for legacy_environment in (
            {},
            {"WORKERS_REPOSITORY_URL": "not-a-clone-url"},
        ):
            with self.subTest(legacy_environment=legacy_environment):
                with tempfile.TemporaryDirectory() as directory:
                    workspace = Path(directory) / "workspace"
                    workspace.mkdir()
                    (workspace / "README.md").write_text(
                        "# Local audit fixture\n", encoding="utf-8"
                    )
                    marker = Path(directory) / "executed"
                    (workspace / "project.sh").write_text(
                        f'touch "{marker}"\n', encoding="utf-8"
                    )
                    summary = Path(directory) / "summary"
                    result = subprocess.run(
                        ["bash", "--noprofile", "--norc", "-euo", "pipefail", "-c", script],
                        cwd=workspace,
                        env={
                            "PATH": os.environ["PATH"],
                            "GITHUB_WORKSPACE": str(workspace),
                            "GITHUB_STEP_SUMMARY": str(summary),
                            **legacy_environment,
                        },
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    report = summary.read_text(encoding="utf-8")
                    self.assertIn("Files inspected: 2", report)
                    self.assertIn("README files: 1", report)
                    self.assertIn("Local audit fixture", report)
                    self.assertIn("This report inspects this repository only.", report)
                    self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()

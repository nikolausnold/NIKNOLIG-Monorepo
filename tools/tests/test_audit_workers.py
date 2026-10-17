import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "audit-workers.yml"


class AuditWorkersTests(unittest.TestCase):
    def test_workflow_uses_read_only_local_checkout_without_workers_secrets(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("contents: read", workflow)
        self.assertIn("uses: actions/checkout@", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertNotIn("secrets.", workflow)
        self.assertNotIn("WORKERS_REPOSITORY_URL", workflow)
        self.assertNotIn("WORKERS_REPO_READ_PAT", workflow)
        self.assertNotIn("git clone", workflow)
        self.assertNotIn("repository:", workflow)
        self.assertIn('"$GITHUB_WORKSPACE" "$GITHUB_STEP_SUMMARY"', workflow)

    def run_audit(self, workspace, summary):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        script = textwrap.dedent(workflow.split("        run: |\n", 1)[1])
        result = subprocess.run(
            ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", script],
            cwd=workspace,
            env={
                "PATH": os.environ["PATH"],
                "GITHUB_WORKSPACE": str(workspace),
                "GITHUB_STEP_SUMMARY": str(summary),
            },
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        return summary.read_text(encoding="utf-8")

    def test_audit_succeeds_without_secrets_and_does_not_execute_project_code(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            workspace = temporary / "repository with spaces"
            workspace.mkdir()
            summary = temporary / "summary.md"
            (workspace / "README.md").write_text("# Local audit fixture\n", encoding="utf-8")
            (workspace / ".github" / "workflows").mkdir(parents=True)
            (workspace / ".github" / "workflows" / "fixture.yml").write_text(
                "name: Fixture\n", encoding="utf-8",
            )
            (workspace / "project.py").write_text(
                "from pathlib import Path\nPath('executed').touch()\n", encoding="utf-8",
            )
            (workspace / "project.sh").write_text("touch executed\n", encoding="utf-8")
            (workspace / ".git").mkdir()
            (workspace / ".git" / "ignored.txt").write_text("ignored\n", encoding="utf-8")
            report = self.run_audit(workspace, summary)
            self.assertIn("- Files inspected: 4\n", report)
            self.assertIn("- README files: 1\n", report)
            self.assertIn("- Workflow files: 1\n", report)
            self.assertIn("`README.md`: # Local audit fixture", report)
            self.assertIn("`.github/workflows/fixture.yml`", report)
            self.assertIn("none detected by basic pattern scan", report)
            self.assertFalse((workspace / "executed").exists())

    def test_audit_handles_an_empty_repository_without_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            workspace = temporary / "empty"
            workspace.mkdir()
            report = self.run_audit(workspace, temporary / "summary.md")
            self.assertIn("- Files inspected: 0\n", report)
            self.assertIn("- No Markdown headings found.", report)
            self.assertIn("## Existing workflows\n- None found.", report)


if __name__ == "__main__":
    unittest.main()

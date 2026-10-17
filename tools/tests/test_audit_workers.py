import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/audit-workers.yml"


class AuditWorkersTests(unittest.TestCase):
    def test_workflow_uses_read_only_local_checkout_without_external_secrets(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        for setting in (
            "workflow_dispatch:",
            "permissions:\n  contents: read",
            "uses: actions/checkout@",
            "persist-credentials: false",
            'python3 - "$GITHUB_WORKSPACE" "$GITHUB_STEP_SUMMARY"',
        ):
            with self.subTest(setting=setting):
                self.assertIn(setting, workflow)
        for removed_dependency in (
            "WORKERS_REPOSITORY_URL",
            "WORKERS_REPO_READ_PAT",
            "secrets.",
            "git clone",
        ):
            with self.subTest(dependency=removed_dependency):
                self.assertNotIn(removed_dependency, workflow)

    def run_audit(self, root, summary, external_env):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        command = textwrap.dedent(workflow.split("        run: |\n", 1)[1])
        env = os.environ.copy()
        for name in ("WORKERS_REPOSITORY_URL", "WORKERS_REPO_READ_PAT"):
            env.pop(name, None)
        env.update(external_env)
        env.update(GITHUB_WORKSPACE=str(root), GITHUB_STEP_SUMMARY=str(summary))
        result = subprocess.run(
            ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", command],
            env=env,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return summary.read_text(encoding="utf-8")

    def test_audit_succeeds_without_valid_external_repository_configuration(self):
        for external_env in (
            {},
            {
                "WORKERS_REPOSITORY_URL": "not-a-github-clone-url",
                "WORKERS_REPO_READ_PAT": "",
            },
        ):
            with self.subTest(external_env=external_env), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "workspace"
                root.mkdir()
                (root / "README.md").write_text("# Local audit fixture\n", encoding="utf-8")
                workflows = root / ".github/workflows"
                workflows.mkdir(parents=True)
                (workflows / "fixture.yml").write_text("name: Fixture\n", encoding="utf-8")
                (root / "must-not-run.sh").write_text("exit 1\n", encoding="utf-8")
                report = self.run_audit(root, Path(tmp) / "summary.md", external_env)
                self.assertIn("- Files inspected: 3", report)
                self.assertIn("- README files: 1", report)
                self.assertIn("- Workflow files: 1", report)
                self.assertIn("# Local audit fixture", report)
                self.assertIn("`.github/workflows/fixture.yml`", report)
                self.assertIn("This report inspects this repository only.", report)
                self.assertNotIn("exit 1", report)

    def test_empty_repository_still_produces_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            report = self.run_audit(root, Path(tmp) / "summary.md", {})
            self.assertIn("- Files inspected: 0", report)
            self.assertIn("- No Markdown headings found.", report)
            self.assertIn("- None found.", report)


if __name__ == "__main__":
    unittest.main()

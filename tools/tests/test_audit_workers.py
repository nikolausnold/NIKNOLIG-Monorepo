import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/audit-workers.yml"


class WorkersAuditTests(unittest.TestCase):
    def test_audit_uses_only_local_checkout_without_external_secrets(self):
        workflow = WORKFLOW.read_text()
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

    def test_audit_reports_local_files_without_external_configuration(self):
        workflow = WORKFLOW.read_text()
        script = textwrap.dedent(workflow.split("        run: |\n", 1)[1])
        with tempfile.TemporaryDirectory(prefix="niknolig-audit-test-") as directory:
            root = Path(directory) / "workspace"
            root.mkdir()
            (root / "README.md").write_text("# Local audit fixture\n")
            workflows = root / ".github/workflows"
            workflows.mkdir(parents=True)
            (workflows / "fixture.yml").write_text("name: Fixture\n")
            (root / "project.py").write_text("raise RuntimeError('must not execute')\n")
            summary = Path(directory) / "summary.md"
            environment = dict(os.environ, GITHUB_WORKSPACE=str(root),
                               GITHUB_STEP_SUMMARY=str(summary))
            environment.pop("WORKERS_REPOSITORY_URL", None)
            environment.pop("WORKERS_REPO_READ_PAT", None)
            for url in (None, "not-a-github-clone-url"):
                with self.subTest(legacy_url=url):
                    if url is not None:
                        environment["WORKERS_REPOSITORY_URL"] = url
                    summary.write_text("")
                    result = subprocess.run(
                        ["bash", "-euo", "pipefail", "-c", script],
                        cwd=directory, env=environment, capture_output=True,
                        text=True, timeout=10,
                    )
                    self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                    report = summary.read_text()
                    self.assertIn("- Files inspected: 3", report)
                    self.assertIn("- README files: 1", report)
                    self.assertIn("- Workflow files: 1", report)
                    self.assertIn("Local audit fixture", report)
                    self.assertIn("`.github/workflows/fixture.yml`", report)
                    self.assertIn("This report inspects this repository only.", report)


if __name__ == "__main__":
    unittest.main()

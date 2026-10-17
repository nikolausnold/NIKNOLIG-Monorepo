import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/audit-workers.yml"


class AuditWorkersTests(unittest.TestCase):
    def test_audit_uses_read_only_local_checkout_without_external_secrets(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        for setting in (
            "contents: read",
            "uses: actions/checkout@",
            "persist-credentials: false",
            'python3 - "$GITHUB_WORKSPACE" "$GITHUB_STEP_SUMMARY"',
        ):
            with self.subTest(setting=setting):
                self.assertIn(setting, workflow)
        for external_dependency in (
            "secrets.",
            "WORKERS_REPOSITORY_URL",
            "WORKERS_REPO_READ_PAT",
            "git clone",
            "repository:",
            "token:",
        ):
            with self.subTest(external_dependency=external_dependency):
                self.assertNotIn(external_dependency, workflow)

    def test_audit_generates_summary_without_workers_configuration(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        _, separator, script = workflow.partition("        run: |\n")
        self.assertTrue(separator, "Audit shell step must be present")
        script = textwrap.dedent(script)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            workspace = directory / "repository"
            workspace.mkdir()
            readme = workspace / "README.md"
            readme.write_text("# Local audit fixture\n", encoding="utf-8")
            workflows = workspace / ".github/workflows"
            workflows.mkdir(parents=True)
            fixture_workflow = workflows / "fixture.yml"
            fixture_workflow.write_text("name: Fixture\n", encoding="utf-8")
            summary = directory / "summary.md"
            environment = {
                key: value for key, value in os.environ.items()
                if not key.startswith("WORKERS_")
            }
            environment.update(
                GITHUB_WORKSPACE=str(workspace),
                GITHUB_STEP_SUMMARY=str(summary),
            )
            result = subprocess.run(
                ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", script],
                env=environment,
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = summary.read_text(encoding="utf-8")
            for expected in (
                "# Read-only repository audit",
                "- Files inspected: 2",
                "- README files: 1",
                "- Workflow files: 1",
                "- `README.md`: # Local audit fixture",
                "- `.github/workflows/fixture.yml`",
                "This report inspects this repository only.",
            ):
                with self.subTest(expected=expected):
                    self.assertIn(expected, report)
            self.assertEqual(readme.read_text(encoding="utf-8"), "# Local audit fixture\n")
            self.assertEqual(fixture_workflow.read_text(encoding="utf-8"), "name: Fixture\n")
            self.assertEqual(
                sorted(path.relative_to(workspace).as_posix()
                       for path in workspace.rglob("*") if path.is_file()),
                [".github/workflows/fixture.yml", "README.md"],
            )


if __name__ == "__main__":
    unittest.main()

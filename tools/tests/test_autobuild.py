import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class AutobuildTests(unittest.TestCase):
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

    def test_android_ci_runs_only_android_build_lint_and_test_tasks(self):
        workflow = (ROOT / ".github/workflows/android-build.yml").read_text()
        for app in ("niknolig", "niknolig-defense"):
            for task in ("testDebugUnitTest", "lintDebug", "assembleDebug"):
                with self.subTest(app=app, task=task):
                    self.assertIn(f":{app}:{task}", workflow)
        for platform_neutral_task in (
            "backend/tests",
            "tools/tests",
            "tools.system_updates",
            "mobile-contracts-",
            "system-update-report-",
            "release-readiness-report",
            "xcodebuild",
            "swift",
        ):
            with self.subTest(platform_neutral_task=platform_neutral_task):
                self.assertNotIn(platform_neutral_task, workflow)

    def test_backend_and_tooling_ci_preserves_shared_checks_and_artifacts(self):
        workflow = (ROOT / ".github/workflows/backend-contracts.yml").read_text()
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
        for android_task in ("./gradlew", "assembleDebug", "lintDebug", "testDebugUnitTest", "xcodebuild"):
            with self.subTest(android_task=android_task):
                self.assertNotIn(android_task, workflow)

    def test_release_contract_gate_checks_the_same_commit_without_signing_secrets(self):
        workflow = (ROOT / ".github/workflows/android-release.yml").read_text()
        contracts, signing = workflow.split("  assemble-release:", 1)
        self.assertIn("  contracts:", contracts)
        self.assertIn("python3 -m unittest discover -s backend/tests", contracts)
        self.assertIn("python3 -m unittest discover -s tools/tests", contracts)
        self.assertIn("ref: ${{ github.event.workflow_run.head_sha || github.sha }}", contracts)
        self.assertNotIn("secrets.", contracts)
        self.assertNotIn("environment:", contracts)
        self.assertIn("needs: contracts", signing)
        self.assertNotIn("backend/tests", signing)

    def test_release_readiness_report_is_uploaded_outside_android_ci(self):
        android_workflow = (ROOT / ".github/workflows/android-build.yml").read_text()
        report_workflow = (ROOT / ".github/workflows/release-audit-artifacts.yml").read_text()
        self.assertNotIn("release-readiness-report", android_workflow)
        self.assertIn('workflows: ["Android apps build"]', report_workflow)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", report_workflow)
        self.assertIn("ref: ${{ github.event.workflow_run.head_sha }}", report_workflow)
        self.assertIn("name: release-readiness-report", report_workflow)


if __name__ == "__main__":
    unittest.main()

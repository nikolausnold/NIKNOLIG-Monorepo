import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class AutobuildTests(unittest.TestCase):
    def test_release_only_signs_successful_trusted_main_build_commit(self):
        workflow = (ROOT / ".github/workflows/android-release.yml").read_text()
        for guard in (
            "workflows: [\"Android apps build\", \"Backend contracts and tooling\"]",
            "github.event.workflow_run.conclusion == 'success'",
            "github.event.workflow_run.head_repository.full_name == github.repository",
            "github.event.workflow_run.head_branch == 'main'",
            'fromJSON(\'["push", "schedule", "workflow_dispatch"]\')',
            "ref: ${{ github.event.workflow_run.head_sha || github.sha }}",
            "actions: read",
            "for workflow in android-build.yml backend-contracts.yml; do",
            'gh api --method GET "repos/$GITHUB_REPOSITORY/actions/runs"',
            'repos/$GITHUB_REPOSITORY/actions/runs"',
            'run.get("path") == workflow_path',
            'run.get("head_sha") == release_sha',
            'run.get("conclusion") == "success"',
            "environment: android-release",
            "persist-credentials: false",
            "1000 + GITHUB_RUN_NUMBER",
        ):
            with self.subTest(guard=guard):
                self.assertIn(guard, workflow)
        self.assertNotIn("/actions/workflows/$workflow/runs", workflow)
        self.assertLess(
            workflow.index("- name: Verify validation results for release commit"),
            workflow.index("- name: Validate and stage release keystores"),
        )
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

    def test_android_build_does_not_run_backend_or_tooling_tests(self):
        for workflow_name in ("android-build.yml", "android-release.yml"):
            workflow = (ROOT / ".github/workflows" / workflow_name).read_text()
            with self.subTest(workflow=workflow_name):
                self.assertNotIn("python3 -m unittest", workflow)
                self.assertNotIn("tools.system_updates", workflow)
        build_workflow = (ROOT / ".github/workflows/android-build.yml").read_text()
        self.assertIn("./gradlew :niknolig:assembleDebug :niknolig-defense:assembleDebug", build_workflow)

    def test_android_client_reports_are_preserved_without_claiming_missing_test_success(self):
        workflow = (ROOT / ".github/workflows/android-build.yml").read_text()
        evidence = workflow.split("- name: Preserve backend client test evidence", 1)[1].split(
            "- name: Verify package identities", 1
        )[0]
        self.assertIn("if: always()", evidence)
        self.assertIn("android-health-client-tests-${{ github.sha }}", evidence)
        self.assertIn("if-no-files-found: warn", evidence)
        self.assertIn("retention-days: 7", evidence)
        for app in ("niknolig", "niknolig-defense"):
            self.assertIn(f"apps/{app}/build/test-results/testDebugUnitTest/*.xml", evidence)
            self.assertIn(f"apps/{app}/build/reports/tests/testDebugUnitTest/**", evidence)


if __name__ == "__main__":
    unittest.main()

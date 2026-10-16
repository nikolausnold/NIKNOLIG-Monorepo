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

    def test_platform_neutral_ci_checks_tools_and_exports_shared_contracts(self):
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
        self.assertIn("  contracts:", workflow)
        self.assertIn("  tooling:", workflow)
        for platform_dependency in ("needs:", "./gradlew", "xcodebuild", "setup-java", "secrets."):
            with self.subTest(platform_dependency=platform_dependency):
                self.assertNotIn(platform_dependency, workflow)

    def test_android_ci_is_independent_of_backend_and_tooling(self):
        workflow = (ROOT / ".github/workflows/android-build.yml").read_text()
        self.assertNotIn("backend/tests", workflow)
        self.assertNotIn("tools.system_updates", workflow)
        self.assertNotIn("tools/tests", workflow)
        self.assertNotIn("needs:", workflow)
        self.assertNotIn("xcodebuild", workflow)
        self.assertIn("runs-on: ubuntu-24.04", workflow)
        self.assertEqual(2, workflow.count('      - "apps/**"'))
        self.assertEqual(2, workflow.count('      - "*.gradle.kts"'))
        self.assertNotIn('      - "backend/**"', workflow)
        self.assertNotIn('      - "ios/**"', workflow)
        for app in ("niknolig", "niknolig-defense"):
            for task in ("testDebugUnitTest", "lintDebug", "assembleDebug"):
                with self.subTest(app=app, task=task):
                    self.assertIn(f":{app}:{task}", workflow)

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


if __name__ == "__main__":
    unittest.main()

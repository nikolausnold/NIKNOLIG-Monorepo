import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class AutobuildTests(unittest.TestCase):
    def test_backend_url_validation_avoids_gradle_java_accessor_shadowing(self):
        for app in ("niknolig", "niknolig-defense"):
            build = (ROOT / "apps" / app / "build.gradle.kts").read_text()
            with self.subTest(app=app):
                imports, body = build.split("plugins {", 1)
                self.assertIn("import java.net.URI", imports)
                self.assertIn("import java.net.InetAddress", imports)
                self.assertIn("URI(value)", body)
                self.assertIn("InetAddress.getByName(host)", body)
                self.assertIn('uri.scheme.equals("https", ignoreCase = true)', body)
                self.assertIn("uri.rawUserInfo == null", body)
                self.assertIn('uri.path in listOf("", "/")', body)
                self.assertIn('host != "localhost"', body)
                self.assertIn('host != "backend.invalid"', body)
                self.assertIn("isLoopbackOrUnspecifiedAddress(host)", body)
                self.assertNotIn("java.net.", body)

    def test_release_only_signs_successful_trusted_main_build_commit(self):
        workflow = (ROOT / ".github/workflows/android-release.yml").read_text()
        release_guard = workflow.split("jobs:", 1)[1].split("runs-on:", 1)[0]
        self.assertIn("github.event_name == 'workflow_dispatch'", release_guard)
        self.assertIn("github.ref == 'refs/heads/main'", release_guard)
        self.assertNotIn("vars.", release_guard)
        for guard in (
            "github.event_name == 'workflow_run'",
            "github.event.workflow_run.conclusion == 'success'",
            "github.event.workflow_run.head_repository.full_name == github.repository",
            "github.event.workflow_run.head_branch == 'main'",
            'contains(fromJSON(\'["push", "schedule", "workflow_dispatch"]\'), github.event.workflow_run.event)',
        ):
            with self.subTest(release_guard=guard):
                self.assertIn(guard, release_guard)
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
        url_validation = workflow.split(
            "- name: Validate approved production backend URLs", 1
        )[1].split("- name: Verify validation results for release commit", 1)[0]
        self.assertIn("NIKNOLIG_BACKEND_URL: ${{ vars.NIKNOLIG_BACKEND_URL }}", url_validation)
        self.assertIn(
            "NIKNOLIG_DEFENSE_BACKEND_URL: ${{ vars.NIKNOLIG_DEFENSE_BACKEND_URL }}",
            url_validation,
        )
        self.assertIn('if [[ -z "${value//[[:space:]]/}" ]]', url_validation)
        self.assertIn("Missing $name", url_validation)
        self.assertIn("verifyReleaseBackendUrl", url_validation)
        self.assertNotIn("secrets.", url_validation)
        self.assertLess(
            workflow.index("- name: Validate approved production backend URLs"),
            workflow.index("- name: Validate and stage release keystores"),
        )
        self.assertNotIn("/actions/workflows/$workflow/runs", workflow)
        self.assertLess(
            workflow.index("- name: Verify validation results for release commit"),
            workflow.index("- name: Validate and stage release keystores"),
        )
        self.assertNotIn("pull_request_target", workflow)

    def test_release_backend_url_preflight_runs_before_gradle(self):
        workflow = (ROOT / ".github/workflows/android-release.yml").read_text()
        validation = workflow.split(
            "- name: Validate approved production backend URLs", 1
        )[1].split("- name: Verify validation results for release commit", 1)[0]
        script = textwrap.dedent(validation.split("run: |\n", 1)[1])
        configured = {
            "NIKNOLIG_BACKEND_URL": "https://api.example.com",
            "NIKNOLIG_DEFENSE_BACKEND_URL": "https://defense.example.com",
        }
        cases = [
            (name, value, 0)
            for name in configured
            for value in (None, "", " \t\n")
        ] + [(None, None, exit_code) for exit_code in (0, 23)]
        for name, value, gradle_exit_code in cases:
            with self.subTest(name=name, value=value, gradle_exit_code=gradle_exit_code):
                with tempfile.TemporaryDirectory(dir="/tmp", prefix=".release-preflight-") as directory:
                    workdir = Path(directory)
                    gradlew = workdir / "gradlew"
                    gradlew.write_text(
                        "#!/bin/bash\n"
                        'printf "%s\\n" "$@" "$NIKNOLIG_BACKEND_URL" '
                        '"$NIKNOLIG_DEFENSE_BACKEND_URL" > gradlew-invocation\n'
                        'exit "$MOCK_GRADLE_EXIT_CODE"\n'
                    )
                    gradlew.chmod(0o755)
                    env = {**os.environ, **configured, "MOCK_GRADLE_EXIT_CODE": str(gradle_exit_code)}
                    if name is not None:
                        if value is None:
                            env.pop(name)
                        else:
                            env[name] = value
                    result = subprocess.run(
                        ["bash"],
                        input=script,
                        text=True,
                        capture_output=True,
                        cwd=workdir,
                        env=env,
                        timeout=10,
                    )
                    invocation = workdir / "gradlew-invocation"
                    if name is not None:
                        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                        self.assertFalse(invocation.exists())
                        if value is not None:
                            self.assertIn(f"Missing {name}", result.stdout)
                    else:
                        self.assertEqual(result.returncode, gradle_exit_code, result.stderr)
                        self.assertEqual(
                            invocation.read_text().splitlines(),
                            [
                                ":niknolig:verifyReleaseBackendUrl",
                                ":niknolig-defense:verifyReleaseBackendUrl",
                                "--no-daemon",
                                *configured.values(),
                            ],
                        )

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

    def test_lint_and_unsigned_ios_app_builds_are_required_without_release_claims(self):
        workflow = (ROOT / ".github/workflows/android-build.yml").read_text()
        self.assertIn(":niknolig:lintDebug :niknolig-defense:lintDebug", workflow)
        self.assertIn("android-lint-${{ github.sha }}", workflow)
        for app in ("niknolig", "niknolig-defense"):
            self.assertIn(f"apps/{app}/build/reports/lint-results-debug.*", workflow)
        ios = (ROOT / ".github/workflows/ios-build.yml").read_text()
        for required in (
            "runs-on: macos-15", "xcodebuild -project apps/ios/NIKNOLIG.xcodeproj",
            "-configuration Debug", "-configuration Release",
            '-target "${{ matrix.target }}"',
            "-sdk iphonesimulator", "CODE_SIGNING_ALLOWED=NO",
            "NIKNOLIG_BACKEND_URL=https://niknolig.example.com",
            "NIKNOLIG_DEFENSE_BACKEND_URL=https://defense.example.com",
            "no signed device archive",
        ):
            self.assertIn(required, " ".join(ios.split()))
        self.assertNotIn("secrets.", ios)
        self.assertNotIn("-allowProvisioningUpdates", ios)
        self.assertIn("swift test --package-path modules/support/ios", ios)
        self.assertEqual(ios.count("- tools/validate_ios_backend.py"), 2)


if __name__ == "__main__":
    unittest.main()

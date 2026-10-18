import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class AutobuildTests(unittest.TestCase):
    def test_navigation_bar_theme_is_scoped_to_api_27(self):
        for app in ("niknolig", "niknolig-defense"):
            with self.subTest(app=app):
                res = ROOT / "apps" / app / "src/main/res"
                themes = ET.parse(res / "values/themes.xml").getroot()
                self.assertIsNone(
                    themes.find(".//item[@name='android:windowLightNavigationBar']")
                )
                base = themes.find("style[@name='Base.Theme.Niknolig']")
                self.assertIsNotNone(base)
                self.assertEqual(
                    base.get("parent"), "@android:style/Theme.Material.NoActionBar"
                )
                self.assertEqual(
                    base.find("item[@name='android:navigationBarColor']").text,
                    "@color/dark_background",
                )
                for qualifier in ("values", "values-v27"):
                    theme = ET.parse(res / qualifier / "themes.xml").find(
                        "style[@name='Theme.Niknolig']"
                    )
                    self.assertIsNotNone(theme)
                    self.assertEqual(theme.get("parent"), "Base.Theme.Niknolig")
                self.assertEqual(
                    theme.find("item[@name='android:windowLightNavigationBar']").text,
                    "false",
                )

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

    def test_autobuild_checks_tools_and_exports_shared_contracts(self):
        workflow = (ROOT / ".github/workflows/android-build.yml").read_text()
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


if __name__ == "__main__":
    unittest.main()

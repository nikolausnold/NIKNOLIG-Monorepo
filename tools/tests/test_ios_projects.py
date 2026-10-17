import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APPS = (
    ("niknolig", "Niknolig", "com.niknolig.app.ios"),
    ("niknolig-defense", "NiknoligDefense", "com.niknolig.defense.ios"),
)


class IOSProjectTests(unittest.TestCase):
    def test_shared_schemes_build_and_test_their_own_app(self):
        for directory, name, identifier in APPS:
            with self.subTest(app=name):
                folder = ROOT / "ios" / directory
                project = folder / f"{name}.xcodeproj"
                settings = (project / "project.pbxproj").read_text()
                self.assertIn(f"PRODUCT_BUNDLE_IDENTIFIER = {identifier};", settings)
                self.assertIn("IPHONEOS_DEPLOYMENT_TARGET = 16.0;", settings)
                self.assertIn(f'$(BUILT_PRODUCTS_DIR)/{name}.app/{name}', settings)
                self.assertNotIn("DEVELOPMENT_TEAM", settings)
                self.assertNotIn("CODE_SIGN_ENTITLEMENTS", settings)
                self.assertNotIn("XCSwiftPackageProductDependency", settings)
                scheme = ET.parse(
                    project / "xcshareddata/xcschemes" / f"{name}.xcscheme"
                )
                references = scheme.findall(
                    "./TestAction/Testables/TestableReference/BuildableReference"
                )
                self.assertEqual(
                    [f"{name}Tests"], [ref.attrib["BlueprintName"] for ref in references]
                )
                self.assertTrue((folder / "Sources" / f"{name}App.swift").is_file())
                tests = (folder / "Tests/AppIdentityTests.swift").read_text()
                self.assertIn(f"@testable import {name}", tests)
                self.assertIn("Bundle.main.bundleIdentifier", tests)

    def test_ios_ci_is_separate_and_does_not_sign_or_mask_failure(self):
        workflow = (ROOT / ".github/workflows/ios-build.yml").read_text()
        for required in (
            "runs-on: macos-15",
            "fail-fast: false",
            "contents: read",
            "persist-credentials: false",
            "xcodebuild test",
            "CODE_SIGNING_ALLOWED=NO",
            "set -euo pipefail",
            "if: always()",
            ".xcresult",
        ):
            self.assertIn(required, workflow)
        for forbidden in (
            "gradlew", "setup-java", "backend/tests", "needs:",
            "secrets.", "continue-on-error", "|| true", "pull_request_target",
        ):
            self.assertNotIn(forbidden, workflow)
        for directory, name, _ in APPS:
            self.assertIn(f"app: {directory}", workflow)
            self.assertIn(f"scheme: {name}", workflow)
        self.assertEqual(2, workflow.count('      - "ios/**"'))


if __name__ == "__main__":
    unittest.main()

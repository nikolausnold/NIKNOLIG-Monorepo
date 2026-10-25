import re
import unittest
from pathlib import Path

from tools.validate_ios_backend import validate


class BackendDefaultsTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[2]

    def _read(self, path):
        return (self.ROOT / path).read_text(encoding="utf-8")

    def test_android_overrides_precede_trimmed_nonempty_default(self):
        for module, setting, variable in (
            ("niknolig", "niknoligBackendUrl", "NIKNOLIG_BACKEND_URL"),
            ("niknolig-defense", "niknoligDefenseBackendUrl", "NIKNOLIG_DEFENSE_BACKEND_URL"),
        ):
            with self.subTest(module=module):
                expression = (
                    f'providers.gradleProperty("{setting}")',
                    f'.orElse(providers.environmentVariable("{variable}"))',
                    ".orNull", "?.trim()", "?.takeIf { it.isNotEmpty() }",
                    '?: "https://api.niknolig.com"',
                )
                self.assertRegex(
                    self._read(f"apps/{module}/build.gradle.kts"),
                    r"\s*".join(re.escape(part) for part in expression),
                )

    def test_each_ios_target_defaults_and_validates_debug_and_release(self):
        content = self._read("apps/ios/NIKNOLIG.xcodeproj/project.pbxproj")
        for identity, variable in (
            ("com.niknolig.app", "NIKNOLIG_BACKEND_URL"),
            ("com.niknolig.defense", "NIKNOLIG_DEFENSE_BACKEND_URL"),
        ):
            lines = [
                line.strip() for line in content.splitlines()
                if f"PRODUCT_BUNDLE_IDENTIFIER = {identity};" in line
                and "isa = XCBuildConfiguration;" in line
            ]
            self.assertEqual(2, len(lines), identity)
            configurations = set()
            for line in lines:
                configuration = re.search(r"name = (Debug|Release); \};$", line)
                self.assertIsNotNone(configuration)
                name = configuration.group(1)
                configurations.add(name)
                with self.subTest(identity=identity, configuration=name):
                    origin = re.search(rf'\b{variable} = "([^"]*)";', line)
                    self.assertIsNotNone(origin)
                    self.assertEqual("https://api.niknolig.com", origin.group(1))
                    self.assertIn(f'INFOPLIST_KEY_BackendBaseURL = "$({variable})";', line)
                    validate({
                        "PRODUCT_BUNDLE_IDENTIFIER": identity,
                        "CONFIGURATION": name,
                        variable: origin.group(1),
                    })
            self.assertEqual({"Debug", "Release"}, configurations)


if __name__ == "__main__":
    unittest.main()

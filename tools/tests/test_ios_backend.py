import contextlib
import io
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.validate_ios_backend import VARIABLES, main, validate


ROOT = Path(__file__).resolve().parents[2]


class IOSBackendTests(unittest.TestCase):
    def test_empty_debug_is_allowed_but_release_requires_each_apps_own_url(self):
        for identity, variable in VARIABLES.items():
            other = next(name for name in VARIABLES.values() if name != variable)
            environment = {
                "PRODUCT_BUNDLE_IDENTIFIER": identity,
                other: "https://other.example.com",
            }
            with self.subTest(identity=identity):
                validate({**environment, "CONFIGURATION": "Debug"})
                with self.assertRaisesRegex(ValueError, variable):
                    validate({**environment, "CONFIGURATION": "Release"})

    def test_https_origins_are_accepted_without_network_access(self):
        for identity, variable in VARIABLES.items():
            for configuration in ("Debug", "Release"):
                for value in ("https://api.example.com", "https://defense.example.com:8443/"):
                    with self.subTest(identity=identity, configuration=configuration, value=value):
                        validate({
                            "PRODUCT_BUNDLE_IDENTIFIER": identity,
                            "CONFIGURATION": configuration,
                            variable: value,
                        })

    def test_invalid_origins_fail_in_debug_and_release(self):
        for configuration in ("Debug", "Release"):
            for value in (
                "http://api.example.com", "******example.com",
                "https://api.example.com/path", "https://api.example.com?",
                "https://api.example.com#", "https://localhost",
                "https://sub.localhost.", "https://backend.invalid",
                "https://127.0.0.1", "https://0.0.0.0", "https://[::1]",
                "https://[::]", "https://127.1", "https://2130706433",
                "https://[::ffff:127.0.0.1]", "https://bad..example.com",
                "https://-bad.example.com",
                "https://api.example.com:0", "https://api.example.com:65536",
                "https://api.example.com:bad", "https://bad host.example.com",
                "https://api.example.com\n.evil.com", "https://api%2eexample.com",
                "https://api.example.com\\evil", "$(UNRESOLVED)",
            ):
                with self.subTest(configuration=configuration, value=value):
                    with self.assertRaises(ValueError):
                        validate({
                            "PRODUCT_BUNDLE_IDENTIFIER": "com.niknolig.app",
                            "CONFIGURATION": configuration,
                            "NIKNOLIG_BACKEND_URL": value,
                        })

    def test_unknown_identity_or_configuration_fails_closed(self):
        for environment in ({}, {"PRODUCT_BUNDLE_IDENTIFIER": "com.niknolig.app"}):
            with self.assertRaises(ValueError):
                validate(environment)

    def test_cli_failure_does_not_print_configured_value(self):
        output = io.StringIO()
        with patch.dict("os.environ", {
            "PRODUCT_BUNDLE_IDENTIFIER": "com.niknolig.app",
            "CONFIGURATION": "Release",
            "NIKNOLIG_BACKEND_URL": "******example.com",
        }, clear=True), contextlib.redirect_stderr(output):
            self.assertEqual(main(), 1)
        self.assertIn("NIKNOLIG_BACKEND_URL", output.getvalue())
        self.assertNotIn("private-", output.getvalue())

    def test_both_targets_validate_before_compiling(self):
        project = (ROOT / "apps/ios/NIKNOLIG.xcodeproj/project.pbxproj").read_text()
        self.assertEqual(project.count('name = "Validate backend"'), 2)
        self.assertEqual(project.count("/* Validate backend */, A100"), 2)
        self.assertEqual(project.count("showEnvVarsInLog = 0"), 2)
        self.assertEqual(project.count("tools/validate_ios_backend.py"), 4)


if __name__ == "__main__":
    unittest.main()

import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULES = ("niknolig", "niknolig-defense")
SOURCE_MODULES = (
    "apps/niknolig",
    "apps/niknolig-defense",
    "modules/electro-engel/core",
    "modules/support/core",
)
ANDROID_NS = "{http://schemas.android.com/apk/res/android}"
ALLOWED_PERMISSIONS = {"android.permission.INTERNET"}
FORBIDDEN_SOURCE = re.compile(
    r"AppFunction|appfunctions|com\.android\.billingclient|BillingClient|"
    r"MANAGE_EXTERNAL_STORAGE|READ_SMS|SEND_SMS|READ_CALL_LOG|WRITE_CALL_LOG|"
    r"READ_CONTACTS|WRITE_CONTACTS|MANAGE_CONTACTS|NEARBY_WIFI_DEVICES|"
    r"ACCESS_LOCAL_NETWORK|ACCESS_FINE_LOCATION|ACCESS_COARSE_LOCATION|"
    r"android\.location|NsdManager|MulticastLock"
)


class GooglePlayPolicyTests(unittest.TestCase):
    def test_each_module_declares_only_internet_and_no_restricted_features(self):
        for module in MODULES:
            with self.subTest(module=module):
                manifest = ET.parse(
                    ROOT / f"apps/{module}/src/main/AndroidManifest.xml"
                ).getroot()
                declared = {
                    e.get(f"{ANDROID_NS}name")
                    for e in manifest.iter()
                    if e.tag.startswith("uses-permission")
                }
                self.assertEqual(declared, ALLOWED_PERMISSIONS)
                self.assertEqual(manifest.findall("queries"), [])
                for service in manifest.iter("service"):
                    self.fail("Unreviewed service declared: AppFunctions need review")
                application = manifest.find("application")
                self.assertEqual(application.get(f"{ANDROID_NS}usesCleartextTraffic"), "false")
                self.assertEqual(application.get(f"{ANDROID_NS}allowBackup"), "false")

    def test_sources_and_builds_use_no_restricted_apis_or_billing(self):
        for module_path in SOURCE_MODULES:
            with self.subTest(module=module_path):
                base = ROOT / module_path
                files = [base / "build.gradle.kts", *base.glob("src/main/**/*.kt")]
                for path in files:
                    self.assertIsNone(
                        FORBIDDEN_SOURCE.search(path.read_text(encoding="utf-8")),
                        str(path),
                    )

    def test_both_modules_keep_identical_sdk_levels(self):
        levels = set()
        for module in MODULES:
            text = (ROOT / f"apps/{module}/build.gradle.kts").read_text(encoding="utf-8")
            levels.add(tuple(re.findall(r"(?:compileSdk|targetSdk|minSdk) = (\d+)", text)))
        self.assertEqual(len(levels), 1)


if __name__ == "__main__":
    unittest.main()

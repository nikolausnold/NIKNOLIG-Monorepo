import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ANDROID = "{http://schemas.android.com/apk/res/android}"
APPS = {"niknolig": "com/niknolig/app", "niknolig-defense": "com/niknolig/defense"}


class SupportFlowTests(unittest.TestCase):
    def test_support_is_internal_and_adds_no_network_permissions(self):
        for app in APPS:
            with self.subTest(app=app):
                manifest = ET.parse(ROOT / "apps" / app / "src/main/AndroidManifest.xml")
                activity = next(
                    item for item in manifest.findall("./application/activity")
                    if item.get(ANDROID + "name") == ".SupportActivity"
                )
                self.assertEqual("false", activity.get(ANDROID + "exported"))
                self.assertEqual([], manifest.findall("./uses-permission"))

    def test_landing_support_opens_internal_flow_not_email(self):
        for app, package in APPS.items():
            with self.subTest(app=app):
                source = (ROOT / "apps" / app / "src/main/java" / package / "MainActivity.kt").read_text()
                self.assertIn("Intent(this, SupportActivity::class.java)", source)
                self.assertNotIn("ACTION_SENDTO", source)
                self.assertNotIn("mailto", source)

    def test_email_is_hidden_until_ai_unavailability_and_requires_confirmation(self):
        for app, package in APPS.items():
            with self.subTest(app=app):
                main = ROOT / "apps" / app / "src/main"
                layout = ET.parse(main / "res/layout/activity_support.xml")
                self.assertEqual(
                    "true",
                    layout.getroot().get(ANDROID + "fitsSystemWindows"),
                )
                button = next(
                    item for item in layout.iter("Button")
                    if item.get(ANDROID + "id") == "@+id/support_escalate"
                )
                self.assertEqual("gone", button.get(ANDROID + "visibility"))
                source = (main / "java" / package / "SupportActivity.kt").read_text()
                self.assertIn("private var aiUnavailable = false", source)
                self.assertIn("if (aiUnavailable) View.VISIBLE else View.GONE", source)
                self.assertIn("if (!aiUnavailable) return", source)
                self.assertIn(".setMessage(getString(R.string.support_escalation_consent", source)
                self.assertIn(".setNegativeButton(android.R.string.cancel, null)", source)
                self.assertIn(".setPositiveButton(R.string.support_email_draft)", source)
                self.assertIn('outState.putBoolean("aiUnavailable", aiUnavailable)', source)
                self.assertIn('savedInstanceState?.getBoolean("aiUnavailable")', source)

    def test_draft_uses_only_fixed_resources_and_handles_missing_email_app(self):
        for app, package in APPS.items():
            with self.subTest(app=app):
                source = (
                    ROOT / "apps" / app / "src/main/java" / package / "SupportActivity.kt"
                ).read_text()
                self.assertIn("Intent(Intent.ACTION_SENDTO)", source)
                self.assertIn('mailto:${Uri.encode(getString(R.string.support_email), "@")}', source)
                self.assertIn('?subject=${Uri.encode(getString(R.string.support_email_subject))}', source)
                self.assertIn('&body=${Uri.encode(getString(R.string.support_email_body))}', source)
                self.assertIn("catch (_: ActivityNotFoundException)", source)
                self.assertIn("R.string.support_email_manual", source)
                for forbidden in ("SharedPreferences", "EditText", "EXTRA_STREAM", "HttpURLConnection", "Log."):
                    self.assertNotIn(forbidden, source)

    def test_support_strings_are_localized_and_honest_about_missing_ai(self):
        for app in APPS:
            with self.subTest(app=app):
                main = ROOT / "apps" / app / "src/main"
                locales = {}
                for folder in ("values", "values-en"):
                    resources = ET.parse(main / "res" / folder / "support_strings.xml")
                    locales[folder] = {item.get("name"): item.text for item in resources.findall("string")}
                    self.assertIn("%1$s", locales[folder]["support_escalation_consent"])
                    self.assertIn("%1$s", locales[folder]["support_email_manual"])
                self.assertEqual(locales["values"].keys(), locales["values-en"].keys())
                self.assertIn("Kein KI-Dienst eingerichtet", locales["values"]["support_ai_unavailable"])
                self.assertIn("No AI service is configured", locales["values-en"]["support_ai_unavailable"])
                for folder in ("values", "values-en"):
                    resources = ET.parse(main / "res" / folder / "strings.xml")
                    strings = {item.get("name"): item.text for item in resources.findall("string")}
                    self.assertNotIn("@", strings["support_description"])


if __name__ == "__main__":
    unittest.main()

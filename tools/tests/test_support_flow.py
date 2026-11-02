import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ANDROID = "{http://schemas.android.com/apk/res/android}"
APPS = {"niknolig": "com/niknolig/app", "niknolig-defense": "com/niknolig/defense"}


class SupportFlowTests(unittest.TestCase):
    def test_android_official_website_links_use_product_domains(self):
        websites = {
            "niknolig": "https://niknolig.com/",
            "niknolig-defense": "https://defense.niknolig.com/",
        }
        for app, website in websites.items():
            with self.subTest(app=app):
                main = ROOT / "apps" / app / "src/main"
                for folder in ("values", "values-en"):
                    resources = ET.parse(main / "res" / folder / "strings.xml")
                    strings = {item.get("name"): item for item in resources.findall("string")}
                    self.assertEqual(website, strings["official_website_url"].text)
                    self.assertEqual("false", strings["official_website_url"].get("translatable"))
                layout = ET.parse(main / "res/layout/activity_support.xml")
                button = next(
                    item for item in layout.iter("Button")
                    if item.get(ANDROID + "id") == "@+id/support_website"
                )
                self.assertEqual("48dp", button.get(ANDROID + "minHeight"))
                source = (main / "java" / APPS[app] / "SupportActivity.kt").read_text()
                self.assertIn("Intent(Intent.ACTION_VIEW", source)
                self.assertIn("R.string.official_website_url", source)
                self.assertIn("R.string.support_website_unavailable", source)
                self.assertIn("catch (_: ActivityNotFoundException)", source)
                for folder, label in (
                    ("values", "Offizielle Website öffnen"),
                    ("values-en", "Open official website"),
                ):
                    support = ET.parse(main / "res" / folder / "support_strings.xml")
                    strings = {item.get("name"): item.text for item in support.findall("string")}
                    self.assertEqual(label, strings["support_website_button"])
                    self.assertTrue(strings["support_website_unavailable"])

    def test_support_is_internal_and_only_allows_internet_without_cleartext(self):
        for app in APPS:
            with self.subTest(app=app):
                manifest = ET.parse(ROOT / "apps" / app / "src/main/AndroidManifest.xml")
                activity = next(
                    item for item in manifest.findall("./application/activity")
                    if item.get(ANDROID + "name") == ".SupportActivity"
                )
                self.assertEqual("false", activity.get(ANDROID + "exported"))
                self.assertEqual(
                    ["android.permission.INTERNET"],
                    [item.get(ANDROID + "name") for item in manifest.findall("./uses-permission")],
                )
                self.assertEqual(
                    "false", manifest.find("./application").get(ANDROID + "usesCleartextTraffic")
                )

    def test_landing_support_opens_internal_flow_not_email(self):
        for app, package in APPS.items():
            with self.subTest(app=app):
                source = (ROOT / "apps" / app / "src/main/java" / package / "MainActivity.kt").read_text()
                self.assertIn("Intent(this, SupportActivity::class.java)", source)
                self.assertNotIn("ACTION_SENDTO", source)
                self.assertNotIn("mailto", source)

    def test_email_fallback_is_immediately_available_and_requires_confirmation(self):
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
                self.assertEqual("visible", button.get(ANDROID + "visibility"))
                source = (main / "java" / package / "SupportActivity.kt").read_text()
                self.assertIn("private var backendStatus: Int? = null", source)
                self.assertNotIn("if (backendStatus == null) return", source)
                self.assertNotIn("if (backendStatus != null)", source)
                self.assertIn("BackendHealthClient(BuildConfig.BACKEND_BASE_URL).check()", source)
                self.assertIn("checkButton.visibility = View.VISIBLE", source)
                self.assertIn("checkButton.isEnabled = false", source)
                self.assertIn("checkButton.isEnabled = true", source)
                self.assertNotIn("/v1/ai/support", source)
                self.assertIn(".setMessage(getString(R.string.support_escalation_consent", source)
                self.assertIn(".setNegativeButton(android.R.string.cancel, null)", source)
                self.assertIn(".setPositiveButton(R.string.support_email_draft)", source)
                self.assertIn('outState.putInt("backendStatus", backendStatus ?: 0)', source)
                self.assertIn('savedInstanceState?.getInt("backendStatus")', source)
                self.assertIn("backendStatus ?: R.string.support_ai_unavailable", source)

    def test_shared_support_core_is_used_by_both_apps(self):
        for app in APPS:
            with self.subTest(app=app):
                build = (ROOT / "apps" / app / "build.gradle.kts").read_text()
                self.assertIn('implementation(project(":support-core"))', build)
                main = ROOT / "apps" / app / "src/main"
                package = APPS[app]
                source = (main / "java" / package / "SupportActivity.kt").read_text()
                self.assertIn("SupportAssistant.answer(question)", source)
                self.assertIn("SupportAssistant.diagnose(diagnostic)", source)
                self.assertIn("SupportEscalationQueue(AndroidSupportTicketStore(this))", source)
                self.assertIn("android:saveEnabled=\"false\"", (main / "res/layout/activity_support.xml").read_text())
                store = (main / "java" / package / "AndroidSupportTicketStore.kt").read_text()
                self.assertIn("SharedPreferences", store)
                self.assertNotIn("question", store.lower())
                self.assertNotIn("prompt", store.lower())
                self.assertIn('.put("payload", ticket.encryptedPayload)', store)
                cipher = (main / "java" / package / "AndroidSupportPayloadCipher.kt").read_text()
                self.assertIn("AES/GCM/NoPadding", cipher)
                self.assertIn("AndroidKeyStore", cipher)
                self.assertNotIn(".decrypt(", source)
                self.assertIn("currentTicket.canShareMetadata(supportApp)", source)

    def test_draft_uses_existing_mailto_path_and_handles_missing_email_app(self):
        for app, package in APPS.items():
            with self.subTest(app=app):
                source = (
                    ROOT / "apps" / app / "src/main/java" / package / "SupportActivity.kt"
                ).read_text()
                self.assertIn("Intent(Intent.ACTION_SENDTO)", source)
                self.assertIn('mailto:${Uri.encode(getString(R.string.support_email), "@")}', source)
                self.assertIn('R.string.support_email_subject, started.id', source)
                self.assertIn('R.string.support_email_body,', source)
                self.assertIn("supportQueue?.beginHandoff(currentTicket.id)", source)
                self.assertIn("finishHandoff(started.id, launched = false)", source)
                self.assertIn("finishHandoff(started.id, launched = true)", source)
                self.assertIn("catch (_: ActivityNotFoundException)", source)
                self.assertIn("R.string.support_email_manual", source)
                for forbidden in ("ACTION_SEND)", "EXTRA_STREAM", "HttpURLConnection", "Log."):
                    self.assertNotIn(forbidden, source)
                manifest = ET.parse(
                    ROOT / "apps" / app / "src/main/AndroidManifest.xml"
                )
                self.assertEqual(
                    "false",
                    manifest.find("./application").get(ANDROID + "allowBackup"),
                )
                draft = source.split("val emailIntent =", 1)[1].split("try {", 1)[0]
                for forbidden in ("question", "encryptedPayload", "requestKey", "decrypt"):
                    self.assertNotIn(forbidden, draft)
                for folder in ("values", "values-en"):
                    resources = ET.parse(
                        ROOT / "apps" / app / "src/main/res" / folder / "strings.xml"
                    )
                    body = next(item.text for item in resources.findall("string")
                                if item.get("name") == "support_email_body")
                    self.assertNotIn("%5$s", body)
                    for index in range(1, 5):
                        self.assertIn(f"%{index}$s", body)

    def test_android_local_delete_is_available_for_every_ticket_state(self):
        for app, package in APPS.items():
            with self.subTest(app=app):
                main = ROOT / "apps" / app / "src/main"
                source = (main / "java" / package / "SupportActivity.kt").read_text()
                self.assertIn("supportQueue?.remove(ticketId, supportApp)", source)
                self.assertIn(
                    "if (ticket != null) View.VISIBLE else View.GONE", source
                )
                layout = ET.parse(main / "res/layout/activity_support.xml")
                self.assertTrue(any(
                    item.get(ANDROID + "id") == "@+id/support_delete_ticket"
                    for item in layout.iter("Button")
                ))
                for folder, expected in (("values", "zurückgerufen"), ("values-en", "recalled")):
                    resources = ET.parse(main / "res" / folder / "support_strings.xml")
                    strings = {item.get("name"): item.text for item in resources.findall("string")}
                    self.assertIn(expected, strings["support_ticket_deleted"])

    def test_ticket_queue_is_bounded_and_handoff_is_idempotent(self):
        source = (ROOT / "modules/support/core/src/main/kotlin/org/niknolig/support/SupportEscalationQueue.kt").read_text()
        self.assertIn("const val MAX_TICKETS = 20", source)
        self.assertIn("maxHandoffAttempts: Int = 3", source)
        self.assertIn("HandoffState.UNCERTAIN", source)
        self.assertIn("HandoffState.HANDED_OFF", source)
        self.assertIn("it.app == app && it.requestKey == requestKey", source)
        tests = (ROOT / "modules/support/core/src/test/kotlin/org/niknolig/support/SupportCoreTest.kt").read_text()
        self.assertIn("failedHandoffIsRetainedAndRetriesAreBounded", tests)
        self.assertIn("successfulHandoffCannotBeRetriedAndCanBeCompletedByUser", tests)

    def test_ios_support_uses_shared_core_and_defense_is_not_an_emergency_channel(self):
        ios = ROOT / "apps" / "ios"
        websites = {
            "NIKNOLIGApp.swift": "https://niknolig.com/",
            "NIKNOLIGDefenseApp.swift": "https://defense.niknolig.com/",
        }
        for filename, website in websites.items():
            with self.subTest(app=filename):
                source = (ios / filename).read_text()
                self.assertIn(website, source)
                self.assertIn('Link("Offizielle Website öffnen"', source)
                self.assertIn('Section("Offline-Support")', source)
                self.assertIn("SupportAssistant.answer(question)", source)
                self.assertIn("SupportEscalationQueue", source)
                self.assertIn('Section("E-Mail-Support")', source)
                self.assertIn("Nichts wird automatisch gesendet.", source)
                self.assertNotIn("/v1/ai/support", source)
                self.assertNotIn(".decrypt(", source)
                self.assertIn("currentTicket.canShareMetadata(for:", source)
                self.assertIn('Button("Lokalen Vorgang löschen", role: .destructive', source)
                self.assertIn("supportQueue.remove(ticket.id, app:", source)
                self.assertIn("nicht gelöscht oder zurückgerufen", source)
                draft = source.split("components.queryItems =", 1)[1].split("guard let url", 1)[0]
                for forbidden in ("question", "encryptedPayload", "requestKey", "decrypt"):
                    self.assertNotIn(forbidden, draft)
                self.assertIn("guard ticket?.id == started.id else { return }", source)
        project = (ios / "NIKNOLIG.xcodeproj/project.pbxproj").read_text()
        self.assertIn("SupportCore.swift in NIKNOLIG Sources", project)
        self.assertIn("SupportCore.swift in Defense Sources", project)
        support_package = ROOT / "modules/support/ios/Package.swift"
        self.assertTrue(support_package.is_file())
        support_core = (ROOT / "modules/support/ios/Sources/SupportCore/SupportCore.swift").read_text()
        self.assertIn("AES.GCM.seal", support_core)
        self.assertIn("kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly", support_core)
        defense = (ios / "NIKNOLIGDefenseApp.swift").read_text()
        self.assertIn("kein Notfallkanal", defense)
        self.assertIn("keine Schutz- oder Notruffunktion", defense)
        self.assertIn("örtlichen Rettungsdienste", defense)

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
                self.assertIn("bleibt deaktiviert", locales["values"]["support_ai_unavailable"])
                self.assertIn("disabled", locales["values-en"]["support_ai_unavailable"])
                for folder in ("values", "values-en"):
                    resources = ET.parse(main / "res" / folder / "strings.xml")
                    strings = {item.get("name"): item.text for item in resources.findall("string")}
                    self.assertNotIn("@", strings["support_description"])


if __name__ == "__main__":
    unittest.main()

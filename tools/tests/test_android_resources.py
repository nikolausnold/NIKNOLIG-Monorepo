import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ANDROID = "{http://schemas.android.com/apk/res/android}"


class AndroidResourceTests(unittest.TestCase):
    def test_navigation_bar_theme_preserves_api_26_fallback(self):
        for app in ("niknolig", "niknolig-defense"):
            with self.subTest(app=app):
                resources = ROOT / "apps" / app / "src/main/res"
                base_styles = {
                    style.attrib["name"]: style
                    for style in ET.parse(resources / "values/themes.xml").getroot()
                }
                api27_styles = {
                    style.attrib["name"]: style
                    for style in ET.parse(resources / "values-v27/themes.xml").getroot()
                }
                base = base_styles["BaseTheme.Niknolig"]
                self.assertEqual(
                    "@android:style/Theme.Material.NoActionBar", base.attrib["parent"]
                )
                base_items = {item.attrib["name"]: item.text for item in base}
                self.assertEqual("@color/dark_background", base_items["android:navigationBarColor"])
                self.assertNotIn("android:windowLightNavigationBar", base_items)
                for styles in (base_styles, api27_styles):
                    self.assertEqual(
                        "@style/BaseTheme.Niknolig",
                        styles["Theme.Niknolig"].attrib["parent"],
                    )
                self.assertEqual(
                    {"android:windowLightNavigationBar": "false"},
                    {item.attrib["name"]: item.text for item in api27_styles["Theme.Niknolig"]},
                )
                self.assertIn(
                    "minSdk = 26", (ROOT / "apps" / app / "build.gradle.kts").read_text()
                )

    def test_free_text_inputs_do_not_participate_in_autofill(self):
        for app in ("niknolig", "niknolig-defense"):
            resources = ROOT / "apps" / app / "src/main/res"
            inputs = [
                element
                for layout in (resources / "layout").glob("*.xml")
                for element in ET.parse(layout).iter("EditText")
            ]
            self.assertEqual(2 if app == "niknolig" else 1, len(inputs))
            for element in inputs:
                with self.subTest(app=app, view=element.attrib[ANDROID + "id"]):
                    self.assertEqual("no", element.attrib.get(ANDROID + "importantForAutofill"))


if __name__ == "__main__":
    unittest.main()

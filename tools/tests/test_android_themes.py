import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE_THEME = "@android:style/Theme.Material.NoActionBar"
SHARED_THEME = "@style/Base.Theme.Niknolig"


class AndroidThemeTests(unittest.TestCase):
    def test_navigation_bar_setting_is_api_qualified_and_preserves_shared_theme(self):
        for app in ("niknolig", "niknolig-defense"):
            resources = ROOT / "apps" / app / "src/main/res"
            with self.subTest(app=app):
                base = ET.parse(resources / "values/themes.xml").getroot()
                default_theme = base.find("style[@name='Theme.Niknolig']")
                shared_theme = base.find("style[@name='Base.Theme.Niknolig']")
                self.assertIsNotNone(default_theme)
                self.assertIsNotNone(shared_theme)
                self.assertEqual(SHARED_THEME, default_theme.get("parent"))
                self.assertEqual(BASE_THEME, shared_theme.get("parent"))
                self.assertIsNone(
                    base.find(".//item[@name='android:windowLightNavigationBar']")
                )

                shared_items = {
                    item.get("name"): item.text for item in shared_theme.findall("item")
                }
                self.assertEqual(
                    "@color/dark_background",
                    shared_items["android:navigationBarColor"],
                )
                self.assertEqual("false", shared_items["android:windowLightStatusBar"])

                qualified = ET.parse(
                    resources / "values-v27/themes.xml"
                ).getroot().find("style[@name='Theme.Niknolig']")
                self.assertIsNotNone(qualified)
                self.assertEqual(SHARED_THEME, qualified.get("parent"))
                self.assertEqual(
                    "false",
                    qualified.find(
                        "item[@name='android:windowLightNavigationBar']"
                    ).text,
                )


if __name__ == "__main__":
    unittest.main()

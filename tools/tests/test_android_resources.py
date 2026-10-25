import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class AndroidThemeTests(unittest.TestCase):
    def test_api_26_themes_keep_dark_system_bars_without_api_27_attributes(self):
        for app in ("niknolig", "niknolig-defense"):
            with self.subTest(app=app):
                resources = ET.parse(
                    ROOT / "apps" / app / "src/main/res/values/themes.xml"
                )
                theme = resources.find("./style[@name='Theme.Niknolig']")
                self.assertIsNotNone(theme)
                items = {item.get("name"): item.text for item in theme.findall("item")}
                self.assertNotIn("android:windowLightNavigationBar", items)
                self.assertEqual(
                    "@color/dark_background", items["android:navigationBarColor"]
                )
                self.assertEqual("false", items["android:windowLightStatusBar"])

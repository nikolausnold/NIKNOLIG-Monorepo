import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class AndroidThemeTests(unittest.TestCase):
    def test_navigation_bar_setting_is_api_qualified_and_preserves_base_theme(self):
        for app in ("niknolig", "niknolig-defense"):
            with self.subTest(app=app):
                res = ROOT / "apps" / app / "src/main/res"
                default = ET.parse(res / "values/themes.xml").getroot()
                qualified = ET.parse(res / "values-v27/themes.xml").getroot()
                self.assertIsNone(default.find(
                    ".//item[@name='android:windowLightNavigationBar']"
                ))
                base = default.find("style[@name='Base.Theme.Niknolig']")
                self.assertIsNotNone(base)
                self.assertEqual(
                    base.get("parent"), "@android:style/Theme.Material.NoActionBar"
                )
                for resources in (default, qualified):
                    theme = resources.find("style[@name='Theme.Niknolig']")
                    self.assertIsNotNone(theme)
                    self.assertEqual(theme.get("parent"), base.get("name"))
                setting = qualified.find(
                    "style[@name='Theme.Niknolig']/"
                    "item[@name='android:windowLightNavigationBar']"
                )
                self.assertIsNotNone(setting)
                self.assertEqual(setting.text, "false")

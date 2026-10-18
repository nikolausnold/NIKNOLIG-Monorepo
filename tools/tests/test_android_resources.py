import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class AndroidThemeTests(unittest.TestCase):
    def test_navigation_bar_theme_is_api_qualified(self):
        for app in ("niknolig", "niknolig-defense"):
            with self.subTest(app=app):
                resources = ROOT / "apps" / app / "src/main/res"
                base = ET.parse(resources / "values/themes.xml").getroot()
                self.assertIsNone(
                    base.find(".//item[@name='android:windowLightNavigationBar']")
                )
                shared = base.find("style[@name='Base.Theme.Niknolig']")
                self.assertIsNotNone(shared)
                self.assertEqual(
                    shared.attrib["parent"],
                    "@android:style/Theme.Material.NoActionBar",
                )
                default = base.find("style[@name='Theme.Niknolig']")
                self.assertIsNotNone(default)
                qualified = ET.parse(
                    resources / "values-v27/themes.xml"
                ).getroot().find("style[@name='Theme.Niknolig']")
                self.assertIsNotNone(qualified)
                self.assertEqual(default.attrib["parent"], "Base.Theme.Niknolig")
                self.assertEqual(qualified.attrib["parent"], default.attrib["parent"])
                self.assertEqual(
                    qualified.find(
                        "item[@name='android:windowLightNavigationBar']"
                    ).text,
                    "false",
                )

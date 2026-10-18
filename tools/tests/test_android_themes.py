import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class AndroidThemeTests(unittest.TestCase):
    def test_api_27_themes_keep_explicit_framework_parent(self):
        for module in ("niknolig", "niknolig-defense"):
            resources = ROOT / "apps" / module / "src/main/res"
            with self.subTest(module=module):
                base = ET.parse(resources / "values/themes.xml").getroot()
                qualified = ET.parse(resources / "values-v27/themes.xml").getroot()
                base_theme = base.find("./style[@name='Theme.Niknolig']")
                qualified_theme = qualified.find("./style[@name='Theme.Niknolig']")
                self.assertIsNotNone(base_theme)
                self.assertIsNotNone(qualified_theme)
                for theme in (base_theme, qualified_theme):
                    self.assertEqual(
                        "@android:style/Theme.Material.NoActionBar",
                        theme.get("parent"),
                    )
                item = "./item[@name='android:windowLightNavigationBar']"
                self.assertIsNone(base_theme.find(item))
                self.assertIsNotNone(qualified_theme.find(item))
                self.assertEqual("false", qualified_theme.find(item).text)
                qualified_items = {
                    item.get("name"): item.text for item in qualified_theme
                }
                for item in base_theme:
                    self.assertEqual(
                        item.text, qualified_items.get(item.get("name")),
                        f"{module}: API-27 theme must preserve {item.get('name')}",
                    )


if __name__ == "__main__":
    unittest.main()

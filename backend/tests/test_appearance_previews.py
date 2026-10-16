"""Structural Android preview guardrails, not device or runtime UI tests."""

from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
ANDROID = "{http://schemas.android.com/apk/res/android}"
MODULES = {"niknolig": "com.niknolig.app", "niknolig-defense": "com.niknolig.defense"}


class AppearancePreviewTests(unittest.TestCase):
    def test_app_boundaries_and_private_preview_entries(self):
        for module, package in MODULES.items():
            with self.subTest(module=module):
                app = ROOT / "apps" / module
                manifest = ET.parse(app / "src/main/AndroidManifest.xml").getroot()
                self.assertEqual([], manifest.findall("uses-permission"))
                self.assertEqual([], manifest.findall("uses-permission-sdk-23"))
                activity = next(
                    item for item in manifest.findall("application/activity")
                    if item.get(ANDROID + "name") == ".AppearancePreviewActivity"
                )
                self.assertEqual("false", activity.get(ANDROID + "exported"))
                self.assertIsNone(activity.find("intent-filter"))
                build = (app / "build.gradle.kts").read_text(encoding="utf-8")
                self.assertIn(f'applicationId = "{package}"', build)
                self.assertNotRegex(build, r"""project\s*\(\s*["']:niknolig""")
                source_dir = app / "src/main/java" / package.replace(".", "/")
                preview = (source_dir / "AppearancePreviewActivity.kt").read_text(encoding="utf-8")
                imports = re.findall(r"^import (.+)$", preview, flags=re.MULTILINE)
                self.assertTrue(imports)
                self.assertTrue(all(item.startswith((
                    "android.app.", "android.os.", "android.view.",
                    "android.widget.", "android.graphics.drawable.",
                )) for item in imports))
                self.assertNotRegex(preview, r"\b(startActivity|sendBroadcast|Thread|Handler|Timer|animate)\s*\(")
                entry = "AssistantActivity" if module == "niknolig" else "MainActivity"
                entry_source = (source_dir / f"{entry}.kt").read_text(encoding="utf-8")
                self.assertIn("AppearancePreviewActivity::class.java", entry_source)
                entry_layout = "activity_assistant" if module == "niknolig" else "activity_main"
                elements = ET.parse(app / f"src/main/res/layout/{entry_layout}.xml").iter()
                self.assertTrue(any(
                    item.get(ANDROID + "id") == "@+id/appearance_preview_button"
                    for item in elements
                ))

    def test_localized_state_sets_and_explicit_simulation(self):
        for module in MODULES:
            for locale in ("values", "values-en"):
                with self.subTest(module=module, locale=locale):
                    resources = ET.parse(
                        ROOT / f"apps/{module}/src/main/res/{locale}/appearance_preview.xml"
                    ).getroot()
                    arrays = {
                        item.get("name"): [child.text for child in item.findall("item")]
                        for item in resources.findall("string-array")
                    }
                    for key in ("preview_situations", "preview_states", "preview_details"):
                        self.assertEqual(5, len(arrays[key]))
                        self.assertEqual(5, len(set(arrays[key])))
                    self.assertEqual(2, len(arrays["preview_devices"]))
                    self.assertEqual(2, len(arrays["preview_surfaces"]))
                    self.assertEqual(["○", "ⓘ", "⋯", "△", "×"],
                                     [item.split()[0] for item in arrays["preview_states"]])
                    strings = {item.get("name"): item.text for item in resources.findall("string")}
                    self.assertIn("Simulation:", strings["preview_target_description"])
                    self.assertIn("Websites", strings["preview_disclaimer"])
                    if module.endswith("defense"):
                        self.assertIn("Defense", strings["preview_disclaimer"])
                    self.assertIn("%1$s", strings["preview_target_description"])
                    self.assertIn("%2$s", strings["preview_target_description"])

    def test_accessible_scroll_layout_and_selection_restoration(self):
        for module, package in MODULES.items():
            with self.subTest(module=module):
                main = ROOT / f"apps/{module}/src/main"
                layout = ET.parse(main / "res/layout/activity_appearance_preview.xml").getroot()
                self.assertEqual("ScrollView", layout.tag)
                by_id = {
                    item.get(ANDROID + "id", "").removeprefix("@+id/"): item
                    for item in layout.iter() if item.get(ANDROID + "id")
                }
                labels = {item.get(ANDROID + "labelFor") for item in layout.iter("TextView")}
                for key in ("situation", "device", "surface"):
                    selector = by_id[f"preview_{key}"]
                    self.assertEqual("Spinner", selector.tag)
                    self.assertEqual("wrap_content", selector.get(ANDROID + "layout_height"))
                    self.assertEqual("dialog", selector.get(ANDROID + "spinnerMode"))
                    self.assertIn(f"@id/preview_{key}", labels)
                self.assertEqual("polite", by_id["preview_status"].get(ANDROID + "accessibilityLiveRegion"))
                self.assertEqual("no", by_id["preview_angel"].get(ANDROID + "importantForAccessibility"))
                self.assertFalse(list(layout.iter("ProgressBar")))
                preview = (main / "java" / package.replace(".", "/") / "AppearancePreviewActivity.kt").read_text(encoding="utf-8")
                for key in ("situation", "device", "surface"):
                    self.assertIn(f'"{key}", savedInstanceState', preview)
                    self.assertIn(f'outState.putInt("{key}", {key}.selectedItemPosition)', preview)
                self.assertIn("state?.getInt(key)", preview)
                self.assertIn("coerceIn(choices.indices)", preview)
                self.assertIn("minOf(available, target)", preview)

    def test_product_silhouettes_and_surfaces_remain_distinct(self):
        vectors = []
        radii = []
        for module in MODULES:
            resources = ROOT / f"apps/{module}/src/main/res"
            vector = ET.parse(resources / "drawable/preview_angel.xml").getroot()
            self.assertEqual("vector", vector.tag)
            vectors.append([path.get(ANDROID + "pathData") for path in vector.findall("path")])
            values = ET.parse(resources / "values/appearance_preview.xml").getroot()
            radii.append(values.find("dimen[@name='preview_corner_radius']").text)
        self.assertNotEqual(vectors[0], vectors[1])
        self.assertEqual(["28dp", "4dp"], radii)

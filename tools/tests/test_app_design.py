import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ANDROID = "{http://schemas.android.com/apk/res/android}"
APPS = ("niknolig", "niknolig-defense")


def resources(app):
    return ROOT / "apps" / app / "src/main/res"


def values(app, filename):
    return {
        element.attrib["name"]: element.text
        for element in ET.parse(resources(app) / "values" / filename).getroot()
    }


def resolve_color(colors, name):
    value = colors[name]
    while value.startswith("@color/"):
        value = colors[value.removeprefix("@color/")]
    return value


def luminance(color):
    channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return sum(channel * weight for channel, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


def contrast(first, second):
    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


class AppDesignTests(unittest.TestCase):
    def test_product_palettes_and_panel_geometry_are_distinct(self):
        expected = {
            "niknolig": ("#101A14", "#1B2A20", "#C8F169", "20dp", "24dp"),
            "niknolig-defense": ("#10151D", "#192330", "#72C7F5", "4dp", "4dp"),
        }
        for app, (background, surface, accent, panel_radius, button_radius) in expected.items():
            with self.subTest(app=app):
                colors = values(app, "colors.xml")
                dimensions = values(app, "dimens.xml")
                self.assertEqual(background, colors["dark_background"])
                self.assertEqual(surface, colors["dark_surface"])
                self.assertEqual(accent, colors["brand_accent"])
                self.assertEqual(panel_radius, dimensions["panel_radius"])
                self.assertEqual(button_radius, dimensions["button_radius"])
                card = ET.parse(resources(app) / "drawable/card_surface.xml").getroot()
                self.assertEqual("@color/dark_surface", card.find("solid").get(ANDROID + "color"))
                self.assertEqual("@dimen/panel_radius", card.find("corners").get(ANDROID + "radius"))
                buttons = ET.parse(resources(app) / "drawable/button_surface.xml").getroot()
                button_states = list(buttons)
                self.assertEqual("false", button_states[0].get(ANDROID + "state_enabled"))
                for button_state in button_states:
                    shape = button_state.find("shape")
                    expected_fill = (
                        "@color/dark_surface"
                        if button_state is button_states[0]
                        else "@color/brand_accent"
                    )
                    self.assertEqual(expected_fill, shape.find("solid").get(ANDROID + "color"))
                    self.assertEqual("@dimen/button_radius", shape.find("corners").get(ANDROID + "radius"))

    def test_brand_marks_and_assistance_motifs_are_product_local(self):
        for name in ("niknolig_mark", "support_avatar"):
            personal = ET.parse(resources("niknolig") / "drawable" / f"{name}.xml").getroot()
            defense = ET.parse(resources("niknolig-defense") / "drawable" / f"{name}.xml").getroot()
            with self.subTest(drawable=name):
                self.assertNotEqual(ET.tostring(personal), ET.tostring(defense))
                for vector in (personal, defense):
                    self.assertEqual("vector", vector.tag)
                    self.assertEqual(vector.get(ANDROID + "viewportWidth"), vector.get(ANDROID + "viewportHeight"))
                    self.assertTrue(any(
                        path.get(ANDROID + "strokeColor") == "@color/brand_accent"
                        for path in vector.iter("path")
                    ))
        personal_mark = ET.parse(resources("niknolig") / "drawable/niknolig_mark.xml")
        defense_mark = ET.parse(resources("niknolig-defense") / "drawable/niknolig_mark.xml")
        self.assertTrue(any(group.get(ANDROID + "rotation") for group in personal_mark.iter("group")))
        self.assertFalse(any(group.get(ANDROID + "rotation") for group in defense_mark.iter("group")))
        self.assertTrue(any(
            path.get(ANDROID + "strokeLineJoin") == "miter"
            for path in defense_mark.iter("path")
        ))

    def test_semantic_text_pairs_meet_wcag_aa_normal_text_contrast(self):
        for app in APPS:
            colors = values(app, "colors.xml")
            pairs = [
                (foreground, background)
                for foreground in ("text_primary", "text_secondary", "brand_accent")
                for background in ("dark_background", "dark_surface")
            ] + [("on_accent", "brand_accent")]
            for foreground, background in pairs:
                with self.subTest(app=app, foreground=foreground, background=background):
                    self.assertGreaterEqual(
                        contrast(resolve_color(colors, foreground), resolve_color(colors, background)),
                        4.5,
                    )

    def test_theme_buttons_have_accessible_wrapping_and_dark_accent_text(self):
        for app in APPS:
            with self.subTest(app=app):
                styles = {
                    style.get("name"): {item.get("name"): item.text for item in style}
                    for style in ET.parse(resources(app) / "values/themes.xml").getroot()
                }
                style_name = styles["Theme.Niknolig"]["android:buttonStyle"].removeprefix("@style/")
                button = styles[style_name]
                self.assertEqual("@drawable/button_surface", button["android:background"])
                self.assertEqual("@color/button_text", button["android:textColor"])
                self.assertEqual("false", button["android:textAllCaps"])
                self.assertEqual("false", button["android:singleLine"])
                self.assertEqual("@null", button["android:stateListAnimator"])
                height = button["android:minHeight"]
                if height.startswith("@dimen/"):
                    height = values(app, "dimens.xml")[height.removeprefix("@dimen/")]
                self.assertTrue(height.endswith("dp"))
                self.assertGreaterEqual(float(height.removesuffix("dp")), 48)

    def test_button_text_colors_match_enabled_and_disabled_backgrounds(self):
        for app in APPS:
            with self.subTest(app=app):
                button_text = ET.parse(resources(app) / "color/button_text.xml").getroot()
                states = list(button_text)
                self.assertEqual("false", states[0].get(ANDROID + "state_enabled"))
                self.assertEqual("@color/text_secondary", states[0].get(ANDROID + "color"))
                self.assertEqual("@color/on_accent", states[1].get(ANDROID + "color"))
                colors = values(app, "colors.xml")
                self.assertGreaterEqual(
                    contrast(
                        resolve_color(colors, "text_secondary"),
                        resolve_color(colors, "dark_surface"),
                    ),
                    4.5,
                )
                self.assertGreaterEqual(
                    contrast(
                        resolve_color(colors, "on_accent"),
                        resolve_color(colors, "brand_accent"),
                    ),
                    4.5,
                )

    def test_layout_buttons_do_not_override_accessible_theme_constraints(self):
        for app in APPS:
            for layout in (resources(app) / "layout").glob("*.xml"):
                for button in ET.parse(layout).iter("Button"):
                    with self.subTest(app=app, layout=layout.name, button=button.get(ANDROID + "id")):
                        self.assertEqual("wrap_content", button.get(ANDROID + "layout_height"))
                        self.assertNotEqual("true", button.get(ANDROID + "singleLine"))
                        self.assertIsNone(button.get(ANDROID + "maxLines"))
                        self.assertIsNone(button.get(ANDROID + "background"))
                        self.assertIsNone(button.get(ANDROID + "textColor"))

    def test_landing_titles_preserve_personal_and_defense_identities(self):
        personal = ET.parse(resources("niknolig") / "layout/activity_main.xml")
        defense = ET.parse(resources("niknolig-defense") / "layout/activity_main.xml")
        personal_titles = [view.get(ANDROID + "text") for view in personal.iter("TextView")]
        defense_titles = [view.get(ANDROID + "text") for view in defense.iter("TextView")]
        self.assertIn("@string/assistant_name", personal_titles)
        self.assertIn("@string/brand_name", personal_titles)
        self.assertIn("@string/brand_name", defense_titles)
        self.assertNotIn("@string/assistant_name", defense_titles)
        brand_title = next(
            view for view in defense.iter("TextView")
            if view.get(ANDROID + "text") == "@string/brand_name"
        )
        self.assertEqual("true", brand_title.get(ANDROID + "accessibilityHeading"))
        self.assertEqual("1", brand_title.get(ANDROID + "layout_weight"))
        self.assertIn("@string/assistant_description", defense_titles)

    def test_landing_support_precedes_system_status_and_profile(self):
        for app in APPS:
            views = list(ET.parse(resources(app) / "layout/activity_main.xml").iter())
            with self.subTest(app=app):
                support = next(
                    index for index, view in enumerate(views)
                    if view.get(ANDROID + "id") == "@+id/support_contact_button"
                )
                status = next(
                    index for index, view in enumerate(views)
                    if view.get(ANDROID + "text") == "@string/system_status_heading"
                )
                profile = next(
                    index for index, view in enumerate(views)
                    if view.get(ANDROID + "id") == "@+id/learning_profile_button"
                )
                self.assertLess(support, status)
                self.assertLess(support, profile)


if __name__ == "__main__":
    unittest.main()

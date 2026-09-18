import copy
import unittest
from validate_video_scene_contract import validate_scene


BASE = {
    "scene_id": "scene-01",
    "role": "cover",
    "duration_seconds": 5.0,
    "ratio": "3:4",
    "style_mode": "editorial",
    "theme": "ink-classic",
    "recipe": "M16-video",
    "motion": "slow-pan",
    "subtitle_safe_area": "bottom-18%",
    "visual_intent": "建立主题并让主体在缩略图中可识别",
    "media": []
}


class VideoSceneContractTests(unittest.TestCase):
    def test_valid_scene(self):
        self.assertEqual(validate_scene(BASE, 0), [])

    def test_style_theme_recipe_and_motion_are_bound(self):
        scene = copy.deepcopy(BASE)
        scene.update(theme="ikb", recipe="S06", motion="unknown")
        errors = validate_scene(scene, 0)
        self.assertTrue(any("theme" in error for error in errors))
        self.assertTrue(any("recipe" in error for error in errors))
        self.assertTrue(any("motion" in error for error in errors))

    def test_missing_layout_fields_are_blocked(self):
        scene = copy.deepcopy(BASE)
        del scene["recipe"]
        errors = validate_scene(scene, 0)
        self.assertIn("scene[0]: missing recipe", errors)


if __name__ == "__main__":
    unittest.main()

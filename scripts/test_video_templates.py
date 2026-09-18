import json
import tempfile
import unittest
from pathlib import Path

import studio
from create_video_scene import create_video_scene
from video_templates import VIDEO_TEMPLATES


class VideoTemplateTests(unittest.TestCase):
    def test_xyzchem_init_uses_vertical_opening_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            studio.init(tmp, preset='xyzchem', language='fr-FR')
            data = studio.read(Path(tmp) / 'project.json')
            scene = data['scenes'][0]
            self.assertEqual((data['profile']['width'], data['profile']['height']), (1080, 1440))
            self.assertEqual(scene['template'], 'opening')
            self.assertEqual(scene['style'], 'swiss')
            self.assertEqual(scene['theme'], 'ikb')
            self.assertEqual(scene['html'], 'scenes/s01/index.html')
            self.assertTrue((Path(tmp) / scene['html']).is_file())
            plan = json.loads((Path(tmp) / 'scenes/s01/plan.json').read_text(encoding='utf-8'))
            self.assertEqual(plan['language'], 'fr-FR')
            self.assertEqual(plan['style'], 'swiss')
            self.assertEqual(plan['theme'], 'ikb')
            self.assertEqual(plan['profile'], {'width': 1080, 'height': 1440})
            html = (Path(tmp) / scene['html']).read_text(encoding='utf-8')
            self.assertIn('data-mode="swiss"', html)
            self.assertIn('data-accent="ikb"', html)

    def test_single_visual_axis_argument_uses_mode_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            studio.init(tmp, preset='xyzchem', style='editorial')
            data = studio.read(Path(tmp) / 'project.json')
            self.assertEqual(data['visual_system'], {'style': 'editorial', 'theme': 'ink-classic'})
            html = (Path(tmp) / data['scenes'][0]['html']).read_text(encoding='utf-8')
            self.assertIn('data-theme="ink-classic"', html)
            self.assertNotIn('data-accent=', html)

    def test_palette_argument_infers_its_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            studio.init(tmp, preset='xyzchem', theme='forest-ink')
            data = studio.read(Path(tmp) / 'project.json')
            self.assertEqual(data['visual_system'], {'style': 'editorial', 'theme': 'forest-ink'})

    def test_create_video_scene_supports_every_template_before_outro(self):
        with tempfile.TemporaryDirectory() as tmp:
            studio.init(tmp, preset='xyzchem')
            data = studio.read(Path(tmp) / 'project.json')
            data['scenes'].append({
                'id': 'outro', 'role': 'brand-outro', 'html': 'scenes/outro/index.html',
                'narration': 'outro', 'caption_phrases': ['outro'], 'claim_ids': [],
                'assets': [], 'dependencies': [], 'beats': [], 'tail_seconds': .25,
            })
            studio.write(Path(tmp) / 'project.json', data)
            for index, template_id in enumerate(sorted(set(VIDEO_TEMPLATES) - {'opening'}), start=2):
                scene_id = f's{index:02d}'
                result = create_video_scene(tmp, scene_id, template_id)
                self.assertEqual(result['template'], template_id)
                self.assertEqual(result['style'], 'swiss')
                self.assertEqual(result['theme'], 'ikb')
                self.assertTrue((Path(tmp) / result['html']).is_file())
            updated = studio.read(Path(tmp) / 'project.json')
            self.assertEqual(updated['scenes'][-1]['id'], 'outro')
            self.assertEqual(len(updated['scenes']), len(VIDEO_TEMPLATES) + 1)

    def test_video_template_rejects_horizontal_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            studio.init(tmp)
            with self.assertRaisesRegex(ValueError, 'require 1080x1440'):
                create_video_scene(tmp, 's02', 'mechanism')

    def test_video_template_does_not_overwrite_scene(self):
        with tempfile.TemporaryDirectory() as tmp:
            studio.init(tmp, preset='xyzchem')
            with self.assertRaisesRegex(ValueError, 'Scene ID already exists'):
                create_video_scene(tmp, 's01', 'opening')

    def test_visual_system_is_fixed_per_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            studio.init(tmp, preset='xyzchem', style='editorial', theme='ink-classic')
            data = studio.read(Path(tmp) / 'project.json')
            self.assertEqual(data['visual_system'], {'style': 'editorial', 'theme': 'ink-classic'})
            with self.assertRaisesRegex(ValueError, 'Visual system is fixed'):
                create_video_scene(tmp, 's02', 'mechanism', 'swiss', 'ikb')


if __name__ == '__main__':
    unittest.main()

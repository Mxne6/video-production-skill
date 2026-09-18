import tempfile
import unittest
import wave
import shutil
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

import attach_brand_outro
import brand_components
import create_brand_outro
import studio
from visual_review import cover_crop_mismatch, estimated_beats, parse_ratio


class StudioCoreTests(unittest.TestCase):
    def test_ffmpeg_prefers_bundled_binary_over_system_path(self):
        bundled = SimpleNamespace(get_ffmpeg_exe=lambda: 'C:/bundled/ffmpeg.exe')
        with (
            patch.dict(studio.os.environ, {}, clear=True),
            patch.dict('sys.modules', {'imageio_ffmpeg': bundled}),
            patch.object(studio.shutil, 'which', return_value='C:/system/ffmpeg.exe'),
        ):
            self.assertEqual(studio.ffmpeg(), 'C:/bundled/ffmpeg.exe')

    def test_brand_outro_template_is_contact_free(self):
        for language in ('zh-CN', 'en', 'fr-FR'):
            text = brand_components.template_path(language).read_text(encoding='utf-8')
            for forbidden in ('400-855-1116', 'www.xyzchem.com', '产品咨询', '访问官网',
                              'PRODUCT ENQUIRIES', 'VISIT OUR WEBSITE', 'LIQUID C-S-H SEEDING'):
                self.assertNotIn(forbidden, text)
            footer = 'INFORMATIONS TECHNIQUES' if language == 'fr-FR' else 'TECHNICAL INFORMATION'
            self.assertIn(footer, text)

    def test_brand_outro_uses_normal_script_audio(self):
        for language in ('zh-CN', 'en'):
            data = studio.read(brand_components.component_path(language))
            self.assertNotIn('audio', data)
            self.assertNotIn('model', data)
            self.assertNotIn('voice', data)
            self.assertGreater(data['estimated_duration_seconds'], 0)
            self.assertIn('complete approved script', data['audio_policy'])

    def test_brand_outro_product_layering_is_explicit_and_consistent(self):
        split = create_brand_outro._split_product
        self.assertEqual(split('XYZCHEM® S7000', 'XYZCHEM®', 'S7000'),
                         ('XYZCHEM®', 'S7000'))
        self.assertEqual(split('新一砼® S7046', None, None),
                         ('新一砼®', 'S7046'))
        self.assertEqual(split('Product', None, None), ('Product', ''))
        with self.assertRaisesRegex(ValueError, '--product must match'):
            split('OTHER S7000', 'XYZCHEM®', 'S7000')

    def test_brand_outro_language_matrix_uses_normal_script_audio(self):
        cases = (
            ('zh-CN', '测试型号 S7000', '测试类别', '南京新义合成科技有限公司是产品提供方。'),
            ('en', 'TEST S7000', 'Test category',
             'Nanjing Xinyi Synthesis Technology Co., Ltd.'),
            ('fr-FR', 'TEST S7000', 'Catégorie test',
             'Nanjing Xinyi Synthesis Technology Co., Ltd.'),
        )
        for language, product, category, company_quote in cases:
            with self.subTest(language=language), tempfile.TemporaryDirectory() as tmp:
                studio.init(tmp, preset='xyzchem', language=language, scene_template='opening')
                project = studio.Project(tmp)
                fonts = project.file('assets/fonts')
                fonts.mkdir(parents=True)
                for name in ('Inter.ttf', 'NotoSansSC.ttf', 'IBMPlexMono.ttf'):
                    (fonts / name).write_bytes(b'test font placeholder')
                source = project.file('sources/company.txt')
                source.write_text(company_quote, encoding='utf-8')
                project.data['sources'] = [
                    {'id': 'company-source', 'path': 'sources/company.txt', 'title': 'Company source'},
                ]
                project.data['claims'] = [
                    {'id': 'company-source-claim', 'source_id': 'company-source',
                     'locator': 'line 1', 'quote': company_quote},
                ]
                studio.write(project.file('project.json'), project.data)
                project.file('theme.html').write_text(
                    "<!doctype html><html data-accent='ikb'><body><div class='poster'></div>"
                    '<style>:root{--accent:#002FA7;--paper:#fafaf8;--ink:#0a0a0a;'
                    '--grey-2:#d4d4d2;--grey-3:#737373}</style></body></html>',
                    encoding='utf-8')

                def fake_render(project, index_file, output_file):
                    Image.new('RGB', (1080, 1440), 'white').save(output_file)

                with patch.object(create_brand_outro, '_render_brand_outro', fake_render):
                    create_brand_outro.create_brand_outro(
                        tmp, product, category, 'theme.html', 'design/outro', language)
                design = project.file('design/outro')
                plan = studio.read(design / 'plan.json')
                generated = (design / 'index.html').read_text(encoding='utf-8')
                self.assertNotIn('{{', generated)
                self.assertTrue((design / 'output.png').is_file())
                self.assertEqual(plan['output_hash'], studio.sha(design / 'output.png'))
                self.assertNotIn('audio', plan)
                self.assertNotIn('pending_confirmation', plan)
                self.assertEqual(plan['component'], brand_components.expected_component_id(language))

                result = attach_brand_outro.attach_outro(
                    studio.Project(tmp), 'design/outro', ['company-source-claim'])
                state = studio.read(project.file('state.json'))
                data = studio.read(project.file('project.json'))
                outro = next(scene for scene in data['scenes'] if scene.get('role') == 'brand-outro')
                self.assertEqual(state['audio'], {})
                self.assertNotIn(outro['id'], state['scripts'])
                self.assertNotIn(outro['id'], state['attempts'])
                self.assertEqual(result['script_status'], 'pending_confirmation')
                self.assertIn('complete script approval', result['next'])

    def test_brand_outro_real_render_is_language_consistent(self):
        font_source = Path(os.environ.get('VIDEO_PRODUCTION_FONT_FIXTURE', ''))
        if not font_source.is_dir():
            self.skipTest('real outro font fixtures are not available')
        cases = (
            ('zh-CN', '新一砼® S7046', '粉末晶种早强剂', ''),
            ('en', 'S7000', 'Liquid C-S-H Seed for Early Strength', 'LIQUID C-S-H SEEDING'),
        )
        for language, product, category, kicker in cases:
            with self.subTest(language=language), tempfile.TemporaryDirectory() as tmp:
                studio.init(tmp, preset='xyzchem', language=language, scene_template='opening')
                project = studio.Project(tmp)
                fonts = project.file('assets/fonts')
                fonts.mkdir(parents=True, exist_ok=True)
                for name in ('Inter.ttf', 'NotoSansSC.ttf', 'IBMPlexMono.ttf'):
                    shutil.copyfile(font_source / name, fonts / name)
                project.file('theme.html').write_text(
                    "<!doctype html><html data-accent='ikb'><body><div class='poster'></div>"
                    '<style>:root{--accent:#002FA7;--paper:#fafaf8;--ink:#0a0a0a;'
                    '--grey-2:#d4d4d2;--grey-3:#737373}</style></body></html>',
                    encoding='utf-8')
                output = create_brand_outro.create_brand_outro(
                    tmp, product, category, 'theme.html', 'design/outro', language, kicker)
                self.assertEqual(output.name, 'output.png')
                with Image.open(output) as image:
                    self.assertEqual(image.size, (1080, 1440))
                generated = project.file('design/outro/index.html').read_text(encoding='utf-8')
                self.assertNotIn('{{', generated)
                plan = studio.read(project.file('design/outro/plan.json'))
                self.assertEqual(plan['output_hash'], studio.sha(output))
                self.assertEqual(plan['kicker'], kicker)
                self.assertEqual(plan['product'], product)

    def test_legacy_draft_export_is_not_reported_as_final(self):
        with tempfile.TemporaryDirectory() as tmp:
            studio.init(tmp)
            project = studio.Project(tmp)
            project.data['duration'] = {'mode': 'max', 'seconds': 10}
            expected = studio.digest(['IDENTITY', None, project.data['duration']])
            project.state['export'] = {
                'path': 'draft.mp4', 'hash': 'HASH', 'identity': expected, 'draft': True,
            }
            project.state['draft_export'] = {
                'path': 'newer-draft.mp4', 'hash': 'HASH', 'identity': expected, 'draft': True,
            }
            with (
                patch.object(studio, 'current_captions', return_value={}),
                patch.object(studio, 'review_identity', return_value='IDENTITY'),
                patch.object(studio, 'sha', return_value='HASH'),
            ):
                export_state, draft_state = studio.export_states(project, {'identity': None})
            self.assertEqual(export_state, {})
            self.assertTrue(draft_state['current'])
            self.assertTrue(draft_state['draft'])
            self.assertEqual(draft_state['path'], 'newer-draft.mp4')

    def test_compose_audio_rejects_damaged_cached_wav(self):
        with tempfile.TemporaryDirectory() as tmp:
            studio.init(tmp)
            project = studio.Project(tmp)
            scene = project.data['scenes'][0]
            attempt_dir = project.path / '.history' / 'test-attempt'
            attempt_dir.mkdir(parents=True)
            with wave.open(str(attempt_dir / 'audio.wav'), 'wb') as audio:
                audio.setparams((1, 2, 48000, 0, 'NONE', 'not compressed'))
                audio.writeframes(b'\0' * 4800 * 2)
            studio.write(attempt_dir / 'words.json', [
                {'text': scene['narration'], 'start': 0, 'end': .1},
            ])
            attempt = {'dir': '.history/test-attempt', 'duration': .1, 'key': 'test'}
            with patch.object(project, 'attempt', return_value=attempt):
                bundle = studio.compose_audio(project)
                project.file(bundle['audio']).write_bytes(b'damaged')
                with self.assertRaisesRegex(ValueError, 'Damaged cached narration'):
                    studio.compose_audio(project)

    def test_visual_review_uses_estimated_beats(self):
        scene = {'id': 's01', 'narration': 'abcdefgh', 'beats': [{'id': 'b01', 'after': 'abcd'}]}
        self.assertEqual(estimated_beats(scene, 4.0), [{'id': 'b01', 'at': 2.0}])
        scene['beats'][0]['after'] = 'not-a-prefix'
        with self.assertRaisesRegex(ValueError, 'exact narration prefix'):
            estimated_beats(scene, 4.0)

    def test_visual_review_blocks_cover_crop_for_mismatched_image_ratio(self):
        self.assertEqual(parse_ratio('3:4'), .75)
        self.assertEqual(parse_ratio('1080×1440'), .75)
        exact = {'objectFit': 'cover', 'naturalWidth': 1080, 'naturalHeight': 1440,
                 'width': 540, 'height': 720}
        self.assertIsNone(cover_crop_mismatch(exact))
        mismatch = {'objectFit': 'cover', 'naturalWidth': 1086, 'naturalHeight': 1448,
                    'width': 904, 'height': 361.1875}
        self.assertIn('source 1086x1448', cover_crop_mismatch(mismatch))
        contained = {**mismatch, 'objectFit': 'contain'}
        self.assertIsNone(cover_crop_mismatch(contained))


if __name__ == '__main__':
    unittest.main()

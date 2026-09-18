import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import production_registry as registry


class ProductionRegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.registry = root / 'records' / 'production-registry.json'
        self.table = root / 'records' / 'production-registry.md'
        self.patch = patch.multiple(registry, REGISTRY=self.registry, TABLE=self.table)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_done_export_is_recorded_and_duplicate_is_blocked(self):
        export = Path(self.tmp.name) / 'video.mp4'
        export.write_bytes(b'video')
        registry.record('S7000', 'zh-CN', 'in_progress', project=self.tmp.name)
        registry.record('s7000', 'en', 'done', export=str(export))
        self.assertTrue(registry.check('S7000', 'en')['can_start'] is False)
        self.assertEqual(registry.check('S7000', 'zh-CN')['state'], 'in_progress')
        self.assertEqual(registry.check('S7000', 'en')['state'], 'done')
        with self.assertRaisesRegex(ValueError, 'already done'):
            registry.record('S7000', 'en', 'done', export=str(export))
        registry.record('S7000', 'en', 'done', export=str(export), force=True)

    def test_done_requires_an_existing_export(self):
        with self.assertRaisesRegex(ValueError, 'does not exist'):
            registry.record('S7000', 'en', 'done', export='missing.mp4')

    def test_registry_markdown_has_both_languages_and_status(self):
        export = Path(self.tmp.name) / 'video.mp4'
        export.write_bytes(b'video')
        registry.record('S7000', 'en', 'done', export=str(export))
        table = self.table.read_text(encoding='utf-8')
        self.assertIn('| S7000 | 未制作 | 已完成 |', table)
        self.assertIn('产品视频生产记录', table)


if __name__ == '__main__':
    unittest.main()

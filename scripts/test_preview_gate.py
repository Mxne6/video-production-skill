import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import studio
from production_contract import check_user_design_review


ROOT = Path(__file__).resolve().parents[1]


class PreviewGateTests(unittest.TestCase):
    def test_preview_requires_explicit_review_and_binds_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            studio.init(project, preset="xyzchem")
            page = project / "design" / "s01"
            page.mkdir(parents=True)
            (page / "output.png").write_bytes(b"png-test")
            shown = subprocess.run(
                [sys.executable, str(ROOT / "scripts/show_design_previews.py"), str(project)],
                capture_output=True, text=True, check=True,
            )
            manifest = json.loads(shown.stdout)
            self.assertEqual(manifest["status"], "pending_user_review")
            self.assertIn("absolute_path", manifest["previews"][0])
            self.assertIsNone(manifest["user_review"])
            review = subprocess.run(
                [sys.executable, str(ROOT / "scripts/record_preview_review.py"), str(project),
                 "--manifest", manifest["manifest_path"], "--status", "approved",
                 "--reviewer", "test-user", "--notes", "逐页检查通过"],
                capture_output=True, text=True, check=True,
            )
            self.assertTrue(review.stdout.strip())
            loaded = studio.Project(project)
            check_user_design_review(loaded, loaded.scenes()[0])

    def test_changed_preview_invalidates_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            studio.init(project, preset="xyzchem")
            page = project / "design" / "s01"
            page.mkdir(parents=True)
            (page / "output.png").write_bytes(b"png-test")
            shown = subprocess.run(
                [sys.executable, str(ROOT / "scripts/show_design_previews.py"), str(project)],
                capture_output=True, text=True, check=True,
            )
            manifest = json.loads(shown.stdout)
            subprocess.run(
                [sys.executable, str(ROOT / "scripts/record_preview_review.py"), str(project),
                 "--manifest", manifest["manifest_path"], "--status", "approved",
                 "--reviewer", "test-user", "--notes", "通过"],
                capture_output=True, text=True, check=True,
            )
            (page / "output.png").write_bytes(b"changed")
            loaded = studio.Project(project)
            with self.assertRaises(ValueError):
                check_user_design_review(loaded, loaded.scenes()[0])


if __name__ == "__main__":
    unittest.main()

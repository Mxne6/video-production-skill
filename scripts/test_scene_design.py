import tempfile
import unittest

import studio
from scene_design import assert_project_design, sequence_report, validate_scene_design


def ready_design(signature='type-left / object-right', family='type-led', dominant='statement'):
    return {
        'status': 'ready',
        'message': 'Understand one supported point.',
        'viewer_task': 'recognize',
        'dominant': dominant,
        'layout_family': family,
        'layout_signature': signature,
        'attention_order': ['primary subject', 'one support line'],
        'on_screen': ['primary subject', 'one support line'],
        'narration_only': ['detail'],
        'image_role': 'none',
        'visual_share': 0.0,
        'density': 'balanced',
        'intensity': 'balanced',
        'contrast_with_previous': 'opening',
        'composition_reason': 'The subject leads; copy only identifies its meaning.',
        'whitespace_reason': 'Protect subtitle and subject silhouette.',
        'continuity_reason': '',
    }


class SceneDesignTests(unittest.TestCase):
    def test_new_xyzchem_project_requires_completed_design_brief(self):
        with tempfile.TemporaryDirectory() as tmp:
            studio.init(tmp, preset='xyzchem')
            project = studio.Project(tmp)
            result = validate_scene_design(project, project.scenes()[0])
            self.assertTrue(result['errors'])
            self.assertEqual(project.data['design_contract_version'], 1)

    def test_ready_brief_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            studio.init(tmp, preset='xyzchem')
            project = studio.Project(tmp)
            scene = project.data['scenes'][0]
            scene['design'] = ready_design()
            scene['visual_plan'] = {'medium': 'typography', 'reason': 'The statement is the visual subject.'}
            result = validate_scene_design(project, scene)
            self.assertEqual(result['errors'], [])

    def test_three_identical_signatures_need_a_content_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            studio.init(tmp, preset='xyzchem')
            project = studio.Project(tmp)
            first = project.data['scenes'][0]
            first['design'] = ready_design('same')
            first['visual_plan'] = {'medium': 'typography', 'reason': 'Controlled typographic comparison.'}
            for index in (2, 3):
                project.data['scenes'].append({
                    **first,
                    'id': f's{index:02d}',
                    'design': ready_design('same'),
                })
            report = sequence_report(project)
            self.assertTrue(any('repeated 3 times' in item for item in report['errors']))
            project.data['scenes'][1]['design']['continuity_reason'] = 'A controlled visual sequence compares the same object state.'
            project.data['scenes'][2]['design']['continuity_reason'] = 'The repeated frame makes the state change directly comparable.'
            self.assertEqual(sequence_report(project)['errors'], [])

    def test_template_name_is_not_a_layout_signature(self):
        with tempfile.TemporaryDirectory() as tmp:
            studio.init(tmp, preset='xyzchem')
            project = studio.Project(tmp)
            scene = project.data['scenes'][0]
            scene['design'] = ready_design(signature='proof-data')
            scene['visual_plan'] = {'medium': 'typography', 'reason': 'The claim is the visual subject.'}
            errors = validate_scene_design(project, scene)['errors']
            self.assertTrue(any('actual silhouette' in item for item in errors))

    def test_ready_brief_must_resolve_visual_medium(self):
        with tempfile.TemporaryDirectory() as tmp:
            studio.init(tmp, preset='xyzchem')
            project = studio.Project(tmp)
            scene = project.data['scenes'][0]
            scene['design'] = ready_design()
            errors = validate_scene_design(project, scene)['errors']
            self.assertTrue(any('resolve visual_plan.medium' in item for item in errors))

    def test_hero_image_must_own_enough_canvas(self):
        with tempfile.TemporaryDirectory() as tmp:
            studio.init(tmp, preset='xyzchem')
            project = studio.Project(tmp)
            design = ready_design(family='image-led', dominant='image')
            design['image_role'] = 'hero'
            design['visual_share'] = .4
            project.data['scenes'][0]['design'] = design
            project.data['scenes'][0]['visual_plan'] = {'medium': 'image', 'reason': 'The image is the evidence.'}
            errors = validate_scene_design(project, project.data['scenes'][0])['errors']
            self.assertTrue(any('visual_share' in item for item in errors))


if __name__ == '__main__':
    unittest.main()

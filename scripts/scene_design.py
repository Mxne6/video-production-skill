"""Validate content-first scene briefs and whole-video visual rhythm."""
from __future__ import annotations

import argparse
import json
import re

VIEWER_TASKS = {'orient', 'recognize', 'explain', 'compare', 'verify', 'conclude', 'feel'}
DOMINANTS = {'statement', 'image', 'product', 'number', 'relationship', 'process', 'evidence'}
LAYOUT_FAMILIES = {'type-led', 'image-led', 'data-led', 'relation-led', 'mixed'}
IMAGE_ROLES = {'none', 'support', 'hero', 'evidence', 'atmosphere'}
DENSITIES = {'sparse', 'balanced', 'dense'}
INTENSITIES = {'quiet', 'balanced', 'strong'}
CONTRASTS = {'opening', 'preserve', 'increase', 'decrease', 'pivot'}
GENERIC_SIGNATURES = {
    'adaptive', 'opening', 'product-hero', 'mechanism', 'proof-data', 'application', 'summary',
    *LAYOUT_FAMILIES,
}


def _text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _list_of_text(value, minimum=0, maximum=None) -> bool:
    return (isinstance(value, list) and len(value) >= minimum
            and (maximum is None or len(value) <= maximum)
            and all(_text(item) for item in value))


def enabled(project) -> bool:
    return int(project.data.get('design_contract_version', 0) or 0) >= 1


def validate_scene_design(project, scene):
    """Return {'errors': [], 'warnings': []}; legacy projects are untouched."""
    result = {'errors': [], 'warnings': []}
    if not enabled(project) or scene.get('role') == 'brand-outro':
        return result
    design = scene.get('design')
    if not isinstance(design, dict):
        result['errors'].append(scene['id'] + ': missing design brief')
        return result
    if design.get('status') != 'ready':
        result['errors'].append(scene['id'] + ': design.status must be ready before review')

    required_text = ('message', 'layout_signature', 'composition_reason')
    for key in required_text:
        if not _text(design.get(key)):
            result['errors'].append(scene['id'] + ': design.' + key + ' is required')
    signature = str(design.get('layout_signature') or '').strip().lower()
    if signature in GENERIC_SIGNATURES:
        result['errors'].append(
            scene['id'] + ': layout_signature must describe the actual silhouette, not a template/family label')

    checks = (
        ('viewer_task', VIEWER_TASKS), ('dominant', DOMINANTS),
        ('layout_family', LAYOUT_FAMILIES), ('image_role', IMAGE_ROLES),
        ('density', DENSITIES), ('intensity', INTENSITIES),
        ('contrast_with_previous', CONTRASTS),
    )
    for key, allowed in checks:
        if design.get(key) not in allowed:
            result['errors'].append(scene['id'] + ': invalid design.' + key)

    attention = design.get('attention_order')
    if not _list_of_text(attention, 1, 3):
        result['errors'].append(scene['id'] + ': attention_order needs 1-3 readable stops')
    if not _list_of_text(design.get('on_screen'), 1):
        result['errors'].append(scene['id'] + ': on_screen must list the visible information budget')
    narration_only = design.get('narration_only', [])
    if not _list_of_text(narration_only, 0):
        result['errors'].append(scene['id'] + ': narration_only must be a list of strings')

    share = design.get('visual_share')
    if not isinstance(share, (int, float)) or isinstance(share, bool) or not 0 <= share <= 1:
        result['errors'].append(scene['id'] + ': visual_share must be between 0 and 1')
    elif design.get('image_role') == 'hero' and share < .55:
        result['errors'].append(scene['id'] + ': hero image must materially own the composition (visual_share >= 0.55)')
    elif design.get('image_role') == 'none' and share > .05:
        result['warnings'].append(scene['id'] + ': image_role none but visual_share is non-trivial')

    duration = scene.get('estimated_duration')
    if isinstance(duration, (int, float)) and attention:
        if duration <= 4 and len(attention) > 2:
            result['errors'].append(scene['id'] + ': <=4s scene should have at most 2 attention stops')

    on_screen = design.get('on_screen') or []
    visible = ' '.join(on_screen)
    cjk = len(re.findall(r'[\u3400-\u9fff]', visible))
    words = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9+%./-]*", visible))
    if isinstance(duration, (int, float)) and duration <= 5 and (cjk > 48 or words > 24):
        result['warnings'].append(scene['id'] + ': visible copy is heavy for a <=5s scene; move explanation to narration')

    if design.get('density') == 'sparse' and not _text(design.get('whitespace_reason', '')):
        result['warnings'].append(scene['id'] + ': sparse scene should state why the whitespace is intentional')

    medium = (scene.get('visual_plan') or {}).get('medium')
    if design.get('status') == 'ready' and medium == 'undecided':
        result['errors'].append(
            scene['id'] + ': resolve visual_plan.medium after the scene design brief')
    image_role = design.get('image_role')
    if image_role in {'support', 'hero', 'evidence', 'atmosphere'} and medium not in {'image', 'mixed'}:
        result['errors'].append(
            scene['id'] + ': image_role requires visual_plan.medium image or mixed')
    if image_role == 'none' and medium == 'image':
        result['errors'].append(
            scene['id'] + ': visual_plan.medium image conflicts with image_role none')

    return result


def sequence_report(project):
    report = {'errors': [], 'warnings': [], 'scenes': []}
    if not enabled(project):
        return report
    scenes = [s for s in project.scenes() if s.get('role') != 'brand-outro']
    for scene in scenes:
        result = validate_scene_design(project, scene)
        report['errors'].extend(result['errors'])
        report['warnings'].extend(result['warnings'])
        design = scene.get('design') or {}
        report['scenes'].append({
            'id': scene['id'],
            'layout_signature': design.get('layout_signature'),
            'layout_family': design.get('layout_family'),
            'dominant': design.get('dominant'),
            'image_role': design.get('image_role'),
            'density': design.get('density'),
            'intensity': design.get('intensity'),
        })

    for index in range(2, len(scenes)):
        window = scenes[index-2:index+1]
        designs = [s.get('design') or {} for s in window]
        signatures = [d.get('layout_signature') for d in designs]
        if signatures[0] and len(set(signatures)) == 1:
            reasons = [d.get('continuity_reason', '').strip() for d in designs[1:]]
            if not all(reasons):
                ids = ', '.join(s['id'] for s in window)
                report['errors'].append(ids + ': same layout_signature repeated 3 times without continuity_reason')
        families = [d.get('layout_family') for d in designs]
        if families[0] and len(set(families)) == 1 and len(set(signatures)) > 1:
            report['warnings'].append(', '.join(s['id'] for s in window)
                                      + ': same layout family for 3 scenes; verify the silhouettes are meaningfully different')
        visual_roles = [(d.get('layout_family'), d.get('dominant'), d.get('image_role'))
                        for d in designs]
        if visual_roles[0][0] and len(set(visual_roles)) == 1:
            report['warnings'].append(', '.join(s['id'] for s in window)
                                      + ': same family/dominant/image role for 3 scenes; check for superficial variation')

    if len(scenes) >= 4:
        intensities = [(s.get('design') or {}).get('intensity') for s in scenes]
        if intensities[0] and len(set(intensities)) == 1:
            report['warnings'].append('All body scenes have the same intensity; verify this is story-driven rather than default styling')
    return report


def assert_project_design(project):
    report = sequence_report(project)
    if report['errors']:
        raise ValueError('Scene design contract failed: ' + '; '.join(report['errors']))
    return report


def main():
    from studio import Project
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    args = parser.parse_args()
    project = Project(args.project)
    report = sequence_report(project)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report['errors']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()

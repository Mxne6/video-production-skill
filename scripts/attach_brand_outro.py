"""Attach the fixed company outro and leave its narration in the normal script pass."""
from __future__ import annotations

import argparse
import copy
import json
import shutil
from pathlib import Path

from brand_components import (
    component_path,
    is_english,
    load_component,
    project_language,
    template_path,
    validate_component,
)
from studio import Project, ROOT, need, read, sha, stamp, write


def _claim_list(claim_ids) -> list[str]:
    if isinstance(claim_ids, str):
        claim_ids = claim_ids.split(',')
    result = [str(x).strip() for x in claim_ids if str(x).strip()]
    need(bool(result), 'Bind the company relationship to an existing source claim')
    return result


def _selected_component(p: Project):
    language = project_language(p)
    component_file = component_path(language)
    template_file = template_path(language)
    component = validate_component(load_component(language), language)
    need(Path(component['template']).as_posix() == template_file.relative_to(ROOT).as_posix(),
         'Brand component template metadata does not match its language template')
    declared = p.data.get('brand_component')
    if declared is not None:
        need(declared == component['id'],
             'Brand component does not match project language: expected ' + component['id'])
    return language, component_file, template_file, component


def _scene(component, language, scene_id, claims, duration_seconds, design_source=None):
    english = is_english(language)
    scene = {
        'id': scene_id,
        'role': 'brand-outro',
        'component': component['id'],
        'html': '',
        'narration': component['narration'],
        'caption_phrases': component['caption_phrases'],
        'tail_seconds': component['tail_seconds'],
        'intent': 'Company and product information' if english else '公司与产品信息',
        'visual_notes': ('Fixed neutral company outro PNG is attached as-is; caption bottom is 13%; record actual static review.'
                         if english else '固定中性品牌片尾 PNG 原样接入，字幕底部 13%；不得加入联系方式、访问引导或 CTA。'),
        'content_kind': 'factual',
        'claim_ids': claims,
        'assets': [],
        'dependencies': [],
        'beats': [],
        'pronunciation': [],
        'visual_plan': {'medium': 'typography', 'reason': 'Fixed company outro'},
        'estimated_duration': duration_seconds + component['tail_seconds'],
    }
    if design_source:
        scene['design_source'] = design_source
    return scene


def _check_design(p, design, component, language, component_file, template_file):
    plan = read(p.file(design + '/plan.json'))
    need(plan.get('component') == component['id'],
         'Design was not generated from the current language-specific fixed component')
    need(plan.get('template_hash') == sha(template_file),
         'Design was not generated from the current fixed component template')
    if language in ('en', 'fr-FR'):
        need(plan.get('language') == language,
             'Design language does not match project language')
        need(plan.get('component_hash') == sha(component_file),
             'Design was generated from a changed language component')
    png = p.file(design + '/output.png')
    need(png.is_file(), 'Missing fixed outro output.png')
    return png


def _write_scene_folder(staging, scene, png):
    base = 'scenes/' + scene['id'] + '-' + stamp()
    folder = staging.file(base)
    folder.mkdir(parents=True)
    shutil.copyfile(png, folder / 'output.png')
    scene['html'] = base + '/index.html'
    (folder / 'index.html').write_text(
        '<!doctype html><meta charset="utf-8"><style>html,body{margin:0;width:100%;height:100%;overflow:hidden}img{display:block;width:100%;height:100%;object-fit:contain}#vp-caption{bottom:13%!important}</style><img src="output.png"><script>window.renderAt=()=>{}</script>',
        encoding='utf-8')
    return base, folder


def _attach_scene(p, staging, scene, png, component, language):
    base, _ = _write_scene_folder(staging, scene, png)
    staging.data['brand_component'] = component['id']
    # Keep state scripts/audio/attempts untouched. The outro follows the same
    # script approval, TTS, listening and caption path as every ordinary scene.
    write(p.file('project.json'), staging.data)
    p.data, p.state = staging.data, staging.state
    p.save('brand_outro_attached', scene=scene['id'], component=component['id'])
    return {
        'scene': scene['id'],
        'html': scene['html'],
        'png': base + '/output.png',
        'language': language,
        'component': component['id'],
        'script_status': 'pending_confirmation',
        'next': 'Include this scene in the complete script approval; generate its narration with the other scenes in the normal TTS pass.',
    }


def attach_outro(p, design, claim_ids, scene_id='brand-outro', design_source=None):
    language, component_file, template_file, component = _selected_component(p)
    need(not any(s.get('role') == 'brand-outro' or s.get('id') == scene_id for s in p.scenes()),
         'Outro already present; do not duplicate or overwrite it')
    need(scene_id and all(c.isascii() and (c.isalnum() or c in '_-') for c in scene_id),
         'Unsafe scene ID')
    need((p.data['profile']['width'], p.data['profile']['height']) == (1080, 1440),
         'Fixed outro requires 1080x1440; initialize with --preset xyzchem')
    claims = _claim_list(claim_ids)
    png = _check_design(p, design, component, language, component_file, template_file)
    from PIL import Image
    with Image.open(png) as im:
        need(im.size == (1080, 1440), 'Outro PNG dimensions differ')
    staging = copy.deepcopy(p)
    duration = component.get('estimated_duration_seconds')
    if not isinstance(duration, (int, float)) or duration <= 0:
        duration = 4.5
    scene = _scene(component, language, scene_id, claims, duration, design_source)
    staging.data['scenes'].append(scene)
    # Validate claims and voice payload before touching project files.
    staging.script_hash(scene)
    staging.payload(scene)
    return _attach_scene(p, staging, scene, png, component, language)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    parser.add_argument('--design', required=True)
    parser.add_argument('--claim-ids', required=True)
    parser.add_argument('--scene-id', default='brand-outro')
    args = parser.parse_args()
    print(json.dumps(attach_outro(Project(args.project), args.design,
                                  args.claim_ids.split(','), args.scene_id),
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

"""Create and append one deterministic video-native scene without writing approvals."""
from __future__ import annotations

import argparse
import json

from studio import Project, write
from video_templates import (DEFAULT_STYLE, DEFAULT_THEME, VIDEO_MODES, VIDEO_PROFILE,
                             VIDEO_TEMPLATES, create_scene_files, new_scene_data,
                             validate_visual_system)


def create_video_scene(project, scene_id, template_id, style=None, theme=None):
    p = Project(project)
    if any(scene['id'] == scene_id for scene in p.scenes()):
        raise ValueError('Scene ID already exists: ' + scene_id)
    profile = p.data['profile']
    actual = (profile['width'], profile['height'])
    if actual != VIDEO_PROFILE:
        raise ValueError('Video-native templates require ' + 'x'.join(map(str, VIDEO_PROFILE))
                         + '; project is ' + 'x'.join(map(str, actual)))
    system = p.data.get('visual_system') or {'style': DEFAULT_STYLE, 'theme': DEFAULT_THEME}
    selected_style, selected_theme = validate_visual_system(style or system.get('style'),
                                                             theme or system.get('theme'))
    if (selected_style, selected_theme) != (system.get('style'), system.get('theme')):
        raise ValueError('Visual system is fixed per project: ' + system['style'] + ' / ' + system['theme'])
    scene = new_scene_data(scene_id, template_id, selected_style, selected_theme, p.language())
    p.payload(scene)
    metadata = create_scene_files(p.path, scene_id, template_id, selected_style,
                                  selected_theme, p.language())
    outro_index = next((index for index, item in enumerate(p.data['scenes'])
                        if item.get('role') == 'brand-outro'), None)
    if outro_index is None:
        p.data['scenes'].append(scene)
    else:
        p.data['scenes'].insert(outro_index, scene)
    write(p.file('project.json'), p.data)
    p.save('video_scene_created', scene=scene_id, template=metadata['template'], theme=metadata['theme'])
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    parser.add_argument('--scene', required=True)
    parser.add_argument('--type', dest='template_id', required=True, choices=sorted(VIDEO_TEMPLATES))
    parser.add_argument('--style', choices=sorted(VIDEO_MODES))
    parser.add_argument('--theme', choices=sorted(theme for values in VIDEO_MODES.values() for theme in values))
    args = parser.parse_args()
    print(json.dumps(create_video_scene(args.project, args.scene, args.template_id, args.style, args.theme),
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

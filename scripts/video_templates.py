"""Deterministic video-native scene templates and metadata."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from language_profiles import DEFAULT_LANGUAGE, is_english, normalize_language

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = ROOT / 'templates' / 'video'

VIDEO_TEMPLATES = {
    'opening': {'medium': 'typography', 'estimate': 4.0},
    'product-hero': {'medium': 'mixed', 'estimate': 5.0},
    'mechanism': {'medium': 'diagram', 'estimate': 6.0},
    'proof-data': {'medium': 'mixed', 'estimate': 6.0},
    'application': {'medium': 'image', 'estimate': 5.0},
    'summary': {'medium': 'typography', 'estimate': 4.0},
}
VIDEO_MODES = {
    'swiss': ('ikb', 'lemon-yellow', 'lemon-green', 'safety-orange'),
    'editorial': ('ink-classic', 'indigo-porcelain', 'forest-ink', 'kraft-paper', 'dune',
                  'midnight-ink'),
}
VIDEO_THEMES = frozenset(theme for themes in VIDEO_MODES.values() for theme in themes)
DEFAULT_STYLE = 'swiss'
DEFAULT_THEME = 'ikb'
VIDEO_PROFILE = (1080, 1440)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def validate_scene_id(scene_id: str) -> str:
    if not isinstance(scene_id, str) or not scene_id or any(
            not (char.isascii() and (char.isalnum() or char in '_-')) for char in scene_id):
        raise ValueError('Scene ID must contain only ASCII letters, digits, underscore or hyphen')
    return scene_id


def validate_template(template_id: str) -> str:
    if template_id not in VIDEO_TEMPLATES:
        raise ValueError('Unknown video template: ' + str(template_id))
    return template_id


def validate_visual_system(style: str | None, theme: str | None) -> tuple[str, str]:
    inferred_styles = [mode for mode, themes in VIDEO_MODES.items() if theme in themes]
    if theme and len(inferred_styles) != 1:
        raise ValueError('Unknown social-card palette: ' + str(theme))
    selected_style = style or (inferred_styles[0] if theme else DEFAULT_STYLE)
    if selected_style not in VIDEO_MODES:
        raise ValueError('Unknown social-card style: ' + str(selected_style))
    selected_theme = theme or (DEFAULT_THEME if selected_style == 'swiss' else 'ink-classic')
    if selected_theme not in VIDEO_MODES[selected_style]:
        raise ValueError(selected_theme + ' is not a ' + selected_style + ' social-card theme')
    return selected_style, selected_theme


def create_scene_files(project, scene_id: str, template_id: str, style: str | None = None,
                       theme: str | None = None, language: str = DEFAULT_LANGUAGE) -> dict:
    """Copy one template into a project scene without writing project.json."""
    project = Path(project).resolve()
    scene_id = validate_scene_id(scene_id)
    template_id = validate_template(template_id)
    style, theme = validate_visual_system(style, theme)
    language = normalize_language(language)
    source_html = TEMPLATE_ROOT / (template_id + '.html')
    source_css = TEMPLATE_ROOT / 'video-template.css'
    source_js = TEMPLATE_ROOT / 'video-template.js'
    for source in (source_html, source_css, source_js):
        if not source.is_file():
            raise FileNotFoundError('Missing video template file: ' + str(source))

    relative = Path('scenes') / scene_id
    destination = (project / relative).resolve()
    if not destination.is_relative_to(project):
        raise ValueError('Video scene path escapes project root')
    if destination.exists():
        raise ValueError('Scene directory already exists; use a new scene ID')
    destination.mkdir(parents=True)

    html = source_html.read_text(encoding='utf-8')
    visual_attribute = ('data-accent' if style == 'swiss' else 'data-theme') + '="' + theme + '"'
    html = (html.replace('{{STYLE}}', style)
                .replace('{{VISUAL_ATTRIBUTE}}', visual_attribute)
                .replace('{{LANG}}', language))
    (destination / 'index.html').write_text(html, encoding='utf-8')
    for source, name in ((source_css, 'video-template.css'), (source_js, 'video-template.js')):
        (destination / name).write_bytes(source.read_bytes())

    plan = {
        'version': 1,
        'template': template_id,
        'template_sha256': sha(source_html),
        'support_sha256': {
            'video-template.css': sha(source_css),
            'video-template.js': sha(source_js),
        },
        'style': style,
        'theme': theme,
        'language': language,
        'profile': {'width': VIDEO_PROFILE[0], 'height': VIDEO_PROFILE[1]},
        'status': 'draft',
        'note': 'Starter only: redesign the composition for this content, replace placeholders, and match each image to its final display ratio before review.',
    }
    _write_json(destination / 'plan.json', plan)
    return {
        'dir': relative.as_posix(),
        'html': (relative / 'index.html').as_posix(),
        'plan': (relative / 'plan.json').as_posix(),
        'template': template_id,
        'style': style,
        'theme': theme,
    }


def new_scene_data(scene_id: str, template_id: str, style: str | None, theme: str | None,
                   language: str) -> dict:
    """Return a new scene that is intentionally incomplete until content is authored."""
    scene_id = validate_scene_id(scene_id)
    template_id = validate_template(template_id)
    style, theme = validate_visual_system(style, theme)
    language = normalize_language(language)
    english = is_english(language)
    narration = 'Narration to be written.' if english else '待编写旁白。'
    relative = (Path('scenes') / scene_id).as_posix()
    intents = {
        'opening': 'Open with the product promise' if english else '用产品承诺建立开场',
        'product-hero': 'Show the product as the central subject' if english else '突出产品主体和关键信息',
        'mechanism': 'Explain the mechanism, sequence or relationship' if english else '解释机理、顺序或关系',
        'proof-data': 'Present evidence, comparison or measurable proof' if english else '呈现证据、对比或可核验数据',
        'application': 'Show an application, material detail or operating context' if english else '展示应用、材料细节或使用场景',
        'summary': 'Close with a concise conclusion' if english else '用简短结论收束正文',
    }
    return {
        'id': scene_id,
        'template': template_id,
        'style': style,
        'theme': theme,
        'html': relative + '/index.html',
        'narration': narration,
        'caption_phrases': [narration],
        'intent': intents[template_id],
        'visual_notes': ('Template starter only: redesign the composition for this content, remove placeholders, '
                         'and match every image to its final display ratio.' if english else
                         '模板仅为起点：按本幕内容重新设计构图，删除占位内容，并让图片比例匹配最终图槽。'),
        'claim_ids': [],
        'assets': [],
        'dependencies': [relative + '/video-template.css', relative + '/video-template.js'],
        'beats': [],
        'tail_seconds': .25,
        'visual_plan': {
            'medium': VIDEO_TEMPLATES[template_id]['medium'],
            'reason': intents[template_id],
        },
        'estimated_duration': VIDEO_TEMPLATES[template_id]['estimate'],
    }

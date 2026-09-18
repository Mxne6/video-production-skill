"""Fill and render a language-specific fixed company-outro component.

The command creates the static design handoff, renders the exact final PNG and
writes plan metadata. It does not design a new layout, synthesize TTS or create
an approval record.
"""
from __future__ import annotations

import argparse
import html
import os
import re
import shutil
from pathlib import Path
from urllib.parse import quote

from PIL import Image

from brand_components import (
    CHINESE_LANGUAGE,
    component_path,
    load_component,
    normalize_language,
    project_language,
    template_path,
    validate_component,
)
from studio import ROOT, Project, need, sha, write

OUTRO_WIDTH = 1080
OUTRO_HEIGHT = 1440
MODEL_TOKEN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._/-]*$')


def _selected_language(project: Project, requested: str | None) -> str:
    project_lang = project_language(project)
    if requested is None:
        return project_lang
    selected = normalize_language(requested)
    need(selected == project_lang,
         'Requested brand language must match project.json.language: ' + project_lang)
    return selected


def _split_product(product: str, product_brand: str | None,
                   product_model: str | None) -> tuple[str, str]:
    text = (product or '').strip()
    if product_brand is not None or product_model is not None:
        brand = (product_brand or '').strip()
        model = (product_model or '').strip()
        need(brand or model, 'Explicit product brand and model cannot both be empty')
        rendered = ' '.join(part for part in (brand, model) if part)
        need(not text or text == rendered,
             '--product must match --product-brand plus --product-model when both are supplied')
        return brand, model
    need(text, 'Product cannot be empty')
    parts = text.rsplit(None, 1)
    if len(parts) == 2 and any(c.isdigit() for c in parts[1]) and MODEL_TOKEN.fullmatch(parts[1]):
        return parts[0], parts[1]
    return text, ''


def _base_plan(component, language, component_file, template_file, theme_source,
               theme, colors, product, product_brand, product_model, kicker,
               category, logo_file):
    return {
        'template': component['template'],
        'template_hash': sha(template_file),
        'theme_source': theme_source,
        'theme_hash': sha(theme),
        'colors': colors,
        'product': product,
        'product_brand': product_brand,
        'product_model': product_model,
        'kicker': kicker,
        'category': category,
        'logo_hash': sha(logo_file),
        'visual_review': 'pending',
        'component': component['id'],
        'narration': component['narration'],
        'caption_phrases': component['caption_phrases'],
        'tail_seconds': component['tail_seconds'],
        'estimated_duration_seconds': component['estimated_duration_seconds'],
        'audio_policy': component['audio_policy'],
    }


def _english_plan(base, component, language, component_file):
    base.update({
        'language': language,
        'component_file': component_file.relative_to(ROOT).as_posix(),
        'component_hash': sha(component_file),
        'script_status': component.get('script_status', 'pending_confirmation'),
        'voice_status': component.get('voice_status', 'candidate_not_auditioned'),
        'company_source': component.get('company_source'),
    })
    return base


def _render_brand_outro(project: Project, index_file: Path, output_file: Path):
    """Render only the brand card so no body background or page padding leaks in."""
    from playwright.sync_api import sync_playwright
    from studio import browser_start

    with sync_playwright() as pw:
        browser = browser_start(pw)
        try:
            page = browser.new_page(viewport={'width': OUTRO_WIDTH, 'height': OUTRO_HEIGHT},
                                    device_scale_factor=1)
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(index_file.as_uri(), wait_until='load')
            page.evaluate('async () => { await document.fonts.ready; }')
            page.evaluate(
                'async () => { await Promise.all([...document.images].map(image => image.decode())); }'
            )
            card = page.locator('#company-card')
            need(card.count() == 1, 'Brand outro must contain exactly one #company-card')
            card.screenshot(path=str(output_file), animations='disabled')
            need(not errors, 'Brand outro browser error: ' + '; '.join(errors))
        finally:
            browser.close()
    with Image.open(output_file) as image:
        need(image.size == (OUTRO_WIDTH, OUTRO_HEIGHT),
             f'Brand outro render must be {OUTRO_WIDTH}x{OUTRO_HEIGHT}, got {image.size[0]}x{image.size[1]}')


def create_brand_outro(project, product, category, theme_html, output,
                       requested_language=None, kicker='', product_brand=None,
                       product_model=None):
    p = Project(project)
    language = _selected_language(p, requested_language)
    component_file = component_path(language)
    template_file = template_path(language)
    component = validate_component(load_component(language), language)
    need(Path(component['template']).as_posix() == template_file.relative_to(ROOT).as_posix(),
         'Brand component template metadata does not match its language template')
    need(p.data['profile']['width'] == OUTRO_WIDTH and p.data['profile']['height'] == OUTRO_HEIGHT,
         'Fixed template supports 1080x1440; other ratios require design adaptation')
    theme = p.file(theme_html)
    out = p.file(output)
    need(not out.exists(), 'Output already exists; select a new version')

    brand, model = _split_product(product, product_brand, product_model)
    kicker = (kicker or '').strip()

    from playwright.sync_api import sync_playwright
    from studio import browser_start
    with sync_playwright() as pw:
        browser = browser_start(pw)
        page = browser.new_page(viewport={'width': OUTRO_WIDTH, 'height': OUTRO_HEIGHT})
        page.goto(theme.as_uri())
        page.evaluate('async () => { await document.fonts.ready; }')
        colors = page.evaluate('''()=>{const el=document.querySelector('.poster')||document.body,s=getComputedStyle(el),r=getComputedStyle(document.documentElement);return {ACCENT:document.documentElement.dataset.accent||'custom',COLOR:s.getPropertyValue('--accent').trim()||r.getPropertyValue('--accent').trim(),PAPER:s.getPropertyValue('--paper').trim()||s.backgroundColor,INK:s.getPropertyValue('--ink').trim()||s.color,LINE:s.getPropertyValue('--grey-2').trim()||'#d4d4d4',MUTED:s.getPropertyValue('--grey-3').trim()||'#747474'}}''')
        browser.close()
    need(bool(colors['COLOR']), 'Theme has no --accent; provide a project HTML exposing its actual theme color')
    for value in colors.values():
        need(not any(x in value for x in ('<', '>', '{', '}', ';')), 'Unsafe theme value')
    fontdir = p.file('assets/fonts')
    need(all((fontdir / f).is_file() for f in ('Inter.ttf', 'NotoSansSC.ttf', 'IBMPlexMono.ttf')),
         'Project needs local Inter, NotoSansSC and IBMPlexMono fonts')

    out.mkdir(parents=True)
    logo_file = out / 'logo.png'
    shutil.copyfile(ROOT / 'assets/brand/logo/xyzchem-logo-user.png', logo_file)
    values = {
        **colors,
        'PRODUCT': product,
        'PRODUCT_BRAND': brand,
        'PRODUCT_MODEL': model,
        'KICKER': kicker,
        'CATEGORY': category,
        'LOGO': 'logo.png',
        'FONTS': quote(Path(os.path.relpath(fontdir, out)).as_posix(), safe='/'),
    }
    text = template_file.read_text(encoding='utf-8')
    for key, value in values.items():
        text = text.replace('{{' + key + '}}', html.escape(value, quote=True))
    need('{{' not in text, 'Brand outro template has unreplaced placeholders')
    index_file = out / 'index.html'
    index_file.write_text(text, encoding='utf-8')

    output_file = out / 'output.png'
    _render_brand_outro(p, index_file, output_file)

    plan = _base_plan(component, language, component_file, template_file,
                      theme_html, theme, colors, product, brand, model, kicker,
                      category, logo_file)
    plan['output_hash'] = sha(output_file)
    if language != CHINESE_LANGUAGE:
        plan = _english_plan(plan, component, language, component_file)
    write(out / 'plan.json', plan)
    return output_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    parser.add_argument('--product', required=True)
    parser.add_argument('--product-brand')
    parser.add_argument('--product-model')
    parser.add_argument('--kicker', default='')
    parser.add_argument('--category', required=True)
    parser.add_argument('--theme-html', required=True, help='Existing project HTML, relative to project root')
    parser.add_argument('--output', default='design/company-outro-fixed-v2')
    parser.add_argument('--language', choices=['zh-CN', 'en', 'fr-FR'], default=None)
    args = parser.parse_args()
    print(create_brand_outro(args.project, args.product, args.category,
                             args.theme_html, args.output, args.language, args.kicker,
                             args.product_brand, args.product_model))


if __name__ == '__main__':
    main()

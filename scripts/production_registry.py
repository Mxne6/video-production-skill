"""Human-readable production registry for produced product videos."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from language_profiles import normalize_language
from studio import ROOT, need, read, stamp, write

REGISTRY = ROOT / 'records' / 'production-registry.json'
TABLE = ROOT / 'records' / 'production-registry.md'
STATUSES = {'not_started', 'planned', 'in_progress', 'done'}
LANGUAGES = ('zh-CN', 'en', 'fr-FR')
LABELS = {'zh-CN': '中文', 'en': '英文', 'fr-FR': '法语'}
MARKS = {'not_started': '未制作', 'planned': '已计划', 'in_progress': '制作中', 'done': '已完成'}


def _normalize_status(value):
    text = str(value or '').strip().lower().replace('-', '_').replace(' ', '_')
    aliases = {
        'pending': 'planned', 'todo': 'planned', 'not_started': 'not_started',
        'planned': 'planned', 'in_progress': 'in_progress', 'doing': 'in_progress',
        'done': 'done', 'complete': 'done', 'completed': 'done', 'finished': 'done',
    }
    status = aliases.get(text, text)
    need(status in STATUSES, 'Unsupported production status: ' + str(value))
    return status


def _load():
    if not REGISTRY.is_file():
        return {'version': 1, 'products': {}}
    data = read(REGISTRY)
    need(isinstance(data, dict) and isinstance(data.get('products'), dict), 'Invalid production registry')
    return data


def _product_key(name):
    text = str(name or '').strip()
    need(text, 'Product name is required')
    return text.upper()


def _status_cell(record):
    langs = record.get('languages', {})
    values = [MARKS[langs.get(lang, 'not_started')] for lang in LANGUAGES]
    return values


def _cell(value):
    return str(value or '').replace('|', '\\|').replace('\n', ' ')


def write_markdown(data):
    lines = [
        '# 产品视频生产记录',
        '',
        '此表由 `scripts/production_registry.py rebuild` 生成，事实源为同目录 JSON。开工前先查产品语言状态，完工后登记实际导出文件。',
        '',
        '| 产品 | 中文 | 英文 | 法语 | 最后更新 | 备注 |',
        '| --- | --- | --- | --- | --- | --- |',
    ]
    for key in sorted(data['products']):
        record = data['products'][key]
        zh, en, fr = _status_cell(record)
        lines.append('| ' + ' | '.join([_cell(record.get('name', key)), _cell(zh), _cell(en), _cell(fr),
                                         _cell(record.get('updated_at', '')), _cell(record.get('note', ''))]) + ' |')
    lines.extend(['', '## 最近记录', '', '| 时间 | 产品 | 语言 | 状态 | 导出 |', '| --- | --- | --- | --- | --- |'])
    events = []
    for record in data['products'].values():
        for lang, status in record.get('languages', {}).items():
            events.append((record.get('updated_at', ''), record.get('name', ''), lang, status,
                           record.get('exports', {}).get(lang, '')))
    for at, name, lang, status, export in sorted(events, reverse=True)[:50]:
        lines.append(f'| {_cell(at)} | {_cell(name)} | {_cell(LABELS.get(lang, lang))} | {_cell(MARKS.get(status, status))} | {_cell(export)} |')
    lines.append('')
    TABLE.parent.mkdir(parents=True, exist_ok=True)
    TABLE.write_text('\n'.join(lines), encoding='utf-8')


def _save(data):
    data['version'] = data.get('version', 1)
    write(REGISTRY, data)
    write_markdown(data)


def check(product, language=None):
    data, key = _load(), _product_key(product)
    record = data['products'].get(key)
    try:
        selected = normalize_language(language) if language else None
    except ValueError:
        selected = None
    if not record:
        return {'product': str(product).strip(), 'language': selected or language, 'state': 'not_started',
                'can_start': True, 'message': '尚未登记制作记录，可以开始。'}
    if selected:
        state = record.get('languages', {}).get(selected, 'not_started')
        export = record.get('exports', {}).get(selected, '')
        return {'product': record['name'], 'language': selected, 'state': state,
                'export': export, 'can_start': state != 'done',
                'message': ('该产品此语言已完成，先核对是否重复。' if state == 'done' else '可以继续或开始。')}
    return {'product': record['name'], 'languages': record.get('languages', {}),
            'exports': record.get('exports', {}), 'can_start': True}


def record(product, language, status, project='', export='', note='', force=False):
    data, key = _load(), _product_key(product)
    language = normalize_language(language)
    status = _normalize_status(status)
    record = data['products'].setdefault(key, {'name': str(product).strip(), 'languages': {}, 'exports': {}})
    old = record.get('languages', {}).get(language, 'not_started')
    need(force or old != 'done',
         'This product-language is already done; use --force only for a deliberate new version')
    project_path = Path(project).resolve() if project else None
    if status == 'done':
        selected_export = export
        if not selected_export and project_path:
            state_file = project_path / 'state.json'
            if state_file.is_file():
                selected_export = read(state_file).get('export', {}).get('path', '')
        need(selected_export, 'A done record needs --export or a project with state.json export')
        export_path = Path(selected_export)
        if not export_path.is_absolute() and project_path:
            export_path = project_path / export_path
        export_path = export_path.resolve()
        need(export_path.is_file(), 'Recorded export does not exist: ' + str(export_path))
    else:
        export_path = None
    record['languages'][language] = status
    if project:
        record['projects'] = record.get('projects', {})
        record['projects'][language] = str(Path(project).resolve())
    if export_path:
        try:
            record['exports'][language] = export_path.relative_to(project_path).as_posix() if project_path else str(export_path)
        except ValueError:
            record['exports'][language] = str(export_path)
    if note:
        record['note'] = note.strip()
    record['updated_at'] = stamp()
    _save(data)
    return {'product': record['name'], 'language': language, 'status': status,
            'project': record.get('projects', {}).get(language, ''),
            'export': record.get('exports', {}).get(language, ''), 'table': str(TABLE)}


def list_products():
    data = _load()
    return {'table': str(TABLE), 'products': data.get('products', {})}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['check', 'record', 'list', 'rebuild'])
    parser.add_argument('--product')
    parser.add_argument('--language', choices=sorted(LANGUAGES))
    parser.add_argument('--status', default='planned')
    parser.add_argument('--project', default='')
    parser.add_argument('--export', default='')
    parser.add_argument('--note', default='')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    if args.command == 'check':
        need(args.product, '--product is required')
        result = check(args.product, args.language)
    elif args.command == 'record':
        need(args.product and args.language, '--product and --language are required')
        result = record(args.product, args.language, args.status, args.project,
                        args.export, args.note, args.force)
    elif args.command == 'list':
        result = list_products()
    else:
        result = _load()
        _save(result)
        result = {'table': str(TABLE)}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

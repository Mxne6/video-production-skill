"""Production gates shared by status, paid synthesis and export. No approvals generated."""
import math
from pathlib import Path
from studio import need, read, sha


def positive(value, name):
    need(type(value) in (int, float) and math.isfinite(value) and value > 0,
         name + ' must be a finite positive number')
    return value


def check_spec(p):
    duration = p.data.get('duration')
    if duration is not None:
        need(isinstance(duration, dict) and duration.get('mode') in ('approx', 'max'),
             'duration.mode must be approx or max')
        positive(duration.get('seconds'), 'duration.seconds')
        if 'tolerance_seconds' in duration:
            positive(duration['tolerance_seconds'], 'duration.tolerance_seconds')
    outros = [s for s in p.scenes() if s.get('role') == 'brand-outro']
    from brand_components import CHINESE_COMPONENT_ID, ENGLISH_COMPONENT_ID
    fixed_ids = (CHINESE_COMPONENT_ID, ENGLISH_COMPONENT_ID)
    if p.data.get('brand_component') in fixed_ids or any(s.get('component') in fixed_ids for s in outros):
        profile = p.data['profile']
        need((profile['width'], profile['height']) == (1080, 1440),
             'Fixed brand outro requires 1080x1440; adapt the component before production')
        need(len(outros) == 1 and outros[0] is p.scenes()[-1],
             'Fixed brand component must occur exactly once as the last scene')
    return duration


def duration_check(p, measured=None):
    spec = check_spec(p)
    if spec is None:
        return {'state': 'unspecified', 'note': 'No duration requested in project.json'}
    if measured is None:
        total = 0
        for s in p.scenes():
            try:
                seconds = p.attempt(s)['duration'] + s.get('tail_seconds', .25)
            except (ValueError, KeyError, FileNotFoundError):
                seconds = positive(s.get('estimated_duration'), s['id'] + '.estimated_duration (including pauses/tail)')
            total += math.ceil(seconds * p.data['profile']['fps']) / p.data['profile']['fps']
    else:
        total = positive(measured, 'measured duration')
    limit = spec['seconds']
    over = total > limit + 1e-8
    if spec['mode'] == 'max':
        need(not over, f"Duration {total:.3f}s exceeds maximum {limit:.3f}s ({'estimate' if measured is None else 'measured'}); revise content before proceeding")
    return {'state': 'outside_target' if spec['mode'] == 'approx' and abs(total-limit) > spec.get('tolerance_seconds', 2) else 'within_target',
            'basis': 'estimate' if measured is None else 'measured', 'seconds': total, 'target_seconds': limit, 'mode': spec['mode']}


def content_check(p, s):
    # Existing source-bound scenes need no mechanical migration; unbound scenes need explicit classification.
    kind = s.get('content_kind', 'factual' if s.get('claim_ids') else None)
    need(kind in ('factual', 'nonfactual'), s['id'] + ': classify content_kind for narration AND visible claims')
    if kind == 'factual':
        need(bool(s.get('claim_ids')), s['id'] + ': factual scene needs source claims')
    else:
        need(bool(s.get('nonfactual_reason', '').strip()), s['id'] + ': explain why scene contains no factual claims')
    p.script_hash(s)


def review_metadata(p, s):
    """Bind judgments without making the content key depend on its own review."""
    assets = {a['id']: a for a in p.data.get('assets', [])}
    rows = [assets.get(aid) for aid in s.get('assets', [])]
    path = s.get('design_review')
    return [rows, [path, sha(p.file(path))] if path else None]


def check_validator_evidence(p, report):
    # Old recorded reviews remain valid; new CLI evidence is checked on import/export.
    if 'validator_report' not in report:
        return
    path = report['validator_report']
    html = report.get('source_html')
    files = report.get('files', {})
    need(path in files and html in files, 'Design review must bind validator JSON and source HTML')
    need(sha(p.file(path)) == files[path] and sha(p.file(html)) == files[html],
         'Design validator evidence changed; rerun and prepare a new review')
    result = read(p.file(path))
    need(result.get('scope') == 'upstream-static-checks-and-page-coverage'
         and result.get('status') == 'pass' and result.get('upstream_exit_code') == 0
         and result.get('fails') == 0 and result.get('html_unchanged') is True,
         'Original design validator did not pass')
    need(result.get('expected_pages') == 1 and result.get('checked_pages') == 1,
         'Per-scene design review requires exactly one checked poster')
    need(result.get('html_sha256') == sha(p.file(html)),
         'Design validator refers to different HTML; rerun on the current design')


def check_design_record(p, s, report, accepted_status=('pass',)):
    check_validator_evidence(p, report)
    need(report.get('scene') == s['id'] and report.get('content_key') == p.visual_content_key(s),
         s['id'] + ': design review refers to different scene/content')
    need(report.get('status') in accepted_status and report.get('viewed') is True
         and bool(report.get('reviewer')) and bool(report.get('observed')),
         s['id'] + ': design needs actual viewed review, reviewer and observations')
    files = report.get('files')
    need(isinstance(files, dict) and bool(files), s['id'] + ': design review needs viewed PNG/file hashes')
    need(any(Path(name).suffix.lower() == '.png' for name in files), s['id'] + ': include the viewed PNG')
    for name, expected in files.items():
        need(sha(p.file(name)) == expected, s['id'] + ': changed reviewed design file: ' + name)


def production_gate(p):
    from visual_review import validate_plan
    from scene_design import assert_project_design
    check_spec(p)
    assert_project_design(p)
    validate_plan(p)
    for s in p.scenes():
        content_check(p, s)
        need(p.state['scripts'].get(s['id'], {}).get('hash') == p.script_hash(s),
             s['id'] + ': current script approval required for production')
        path = s.get('design_review')
        need(bool(path), s['id'] + ': missing design_review; record actual static review before export')
        check_design_record(p, s, read(p.file(path)))
    return True

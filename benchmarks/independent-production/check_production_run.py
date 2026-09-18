"""Check evidence for an independent production run; never infer missing usage or reviews."""
import argparse
from pathlib import Path
from studio import read, sha

CHECKS = ('source_traceability', 'design', 'narration', 'captions', 'mp4', 'resume', 'local_edit_reuse')


def check(path):
    path = Path(path).resolve()
    d = read(path)
    missing = []
    for field in ('model', 'reasoning_effort', 'source', 'usage', 'paid_calls', 'interventions', 'checks'):
        if field not in d or d[field] is None: missing.append(field)
    source = d.get('source') or {}
    for field in ('path', 'sha256', 'new_material'):
        if field not in source or source[field] is None: missing.append('source.'+field)
    if source.get('path'):
        f = path.parent/source['path']
        if not f.is_file() or sha(f) != source.get('sha256'): missing.append('source evidence/hash')
    for name in CHECKS:
        item = (d.get('checks') or {}).get(name, {})
        if item.get('status') != 'pass' or not item.get('evidence'): missing.append('checks.'+name)
        else:
            f = path.parent/item['evidence']
            if not f.is_file() or sha(f) != item.get('sha256'): missing.append('checks.'+name+' evidence/hash')
    if not isinstance(d.get('paid_calls'), int) or isinstance(d.get('paid_calls'), bool) or d.get('paid_calls', -1) < 0: missing.append('paid_calls count')
    usage = d.get('usage') or {}
    if usage.get('status') not in ('recorded', 'unavailable') or not usage.get('evidence'): missing.append('usage evidence (or explicit unavailable reason)')
    if not isinstance(d.get('interventions'), list): missing.append('interventions list')
    if not isinstance(d.get('model'), str) or not d.get('model'): missing.append('actual model')
    if not isinstance(d.get('reasoning_effort'), str) or not d.get('reasoning_effort'): missing.append('actual reasoning effort')
    independent = not missing and source.get('new_material') is True and d.get('interventions') == []
    return {'result': 'evidence_complete' if independent else ('incomplete' if missing else 'assisted_or_reused'), 'missing': missing,
            'independence': 'not_verified', 'note': 'Evidence completeness only; model identity, new material, absence of intervention and quality require actual run review.'}


if __name__ == '__main__':
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('record')
    args = parser.parse_args()
    result = check(args.record)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['result'] == 'evidence_complete' else 2)

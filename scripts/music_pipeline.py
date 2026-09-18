"""Project-bound music mixing; no network or paid calls."""
import json
import math
import os
import random
from pathlib import Path
from urllib.parse import quote

import numpy as np

from studio import read, write, sha, digest, need, stamp, compose_audio, ROOT

ENGINE = 'music-1'


def _music_candidates(p):
    config = p.data.get('music') or {}
    rows = config.get('candidates')
    if rows is None:
        rows = [{'id': 'selected', 'source': config['source'], 'license': config['license'],
                 'loop': config.get('loop', False)}]
    need(isinstance(rows, list) and rows, 'music.candidates must be a nonempty list')
    seen, result = set(), []
    for index, row in enumerate(rows):
        need(isinstance(row, dict), 'Music candidate must be an object')
        item = dict(row)
        item['id'] = str(item.get('id') or ('candidate-' + str(index + 1)))
        need(item['id'] not in seen, 'Duplicate music candidate id: ' + item['id'])
        need(item.get('source') and item.get('license'),
             'Music candidate needs source and license: ' + item['id'])
        seen.add(item['id'])
        result.append(item)
    return result


def _selected_music(p):
    config = p.data.get('music') or {}
    rows = _music_candidates(p)
    by_id = {row['id']: row for row in rows}
    selected_id = config.get('selected')
    if selected_id is None:
        selected_id = rows[0]['id']
    need(selected_id in by_id, 'Unknown selected music candidate: ' + str(selected_id))
    row = dict(by_id[selected_id])
    if config.get('source'):
        row['source'] = config['source']
    if config.get('license'):
        row['license'] = config['license']
    if 'loop' in config:
        row['loop'] = config['loop']
    return row


def music_candidates(p):
    selected = _selected_music(p)['id']
    rows = []
    for row in _music_candidates(p):
        source, license_path = p.file(row['source']), p.file(row['license'])
        license_data = read(license_path)
        need(all(license_data.get(k) for k in ('title', 'artist', 'source_url', 'license', 'attribution')), 'Music license record incomplete')
        rows.append({**row, 'title': license_data.get('title', ''), 'artist': license_data.get('artist', ''),
                     'license_name': license_data.get('license', ''), 'active': row['id'] == selected,
                     'source_hash': sha(source), 'license_hash': sha(license_path)})
    return {'selected': selected, 'candidates': rows}


def music_select(p, candidate_id=None, evidence='', method=None, seed=None):
    result = music_candidates(p)
    if candidate_id:
        row = next((x for x in result['candidates'] if x['id'] == candidate_id), None)
        need(row is not None, 'Unknown music candidate: ' + str(candidate_id))
        chosen_by = method or 'explicit'
    else:
        chosen_by = method or 'random'
        actual_seed = int(seed) if seed is not None else random.SystemRandom().randrange(2**63)
        randomizer = random.Random(actual_seed)
        row = randomizer.choice(result['candidates'])
        seed = actual_seed
    config = p.data.setdefault('music', {})
    config['source'], config['license'] = row['source'], row['license']
    config['loop'] = bool(row.get('loop', False))
    config['selected'] = row['id']
    p.state['music_selection'] = {'candidate': row['id'], 'method': chosen_by,
                                  'seed': seed, 'evidence': evidence.strip(), 'at': stamp()}
    p.save('music_selected', candidate=row['id'], method=chosen_by, seed=seed, evidence=evidence.strip())
    return {'selected': row['id'], 'title': row['title'], 'artist': row['artist'],
            'source': row['source'], 'license': row['license'], 'loop': config['loop'],
            'method': chosen_by, 'seed': seed,
            'next': 'Run studio render P --draft to blend the selected track, listen to the mix, then approve it.'}


def decode_music(path, seconds=None, loop=False):
    from mix_background import decode, RATE
    source = decode(path, None if loop else seconds, 'highpass=f=110,lowpass=f=7000')
    needed = None if seconds is None else int(seconds * RATE)
    if loop and needed is not None and len(source) < needed:
        need(len(source) > 0, 'Music source is silent or empty')
        source = np.tile(source, (int(np.ceil(needed / len(source)))+1, 1))
    return source


def spec(p, bundle):
    config = p.data.get('music')
    if not config or config.get('enabled', True) is False:
        return None
    selected = _selected_music(p)
    source, license_path = p.file(selected['source']), p.file(selected['license'])
    license_data = read(license_path)
    need(all(license_data.get(k) for k in ('title', 'artist', 'source_url', 'license', 'attribution')), 'Music license record incomplete')
    gap, offset = config.get('gap_db', 24), config.get('offset_db', 0)
    need(type(gap) in (int, float) and math.isfinite(gap) and 6 <= gap <= 36, 'music.gap_db must be 6..36')
    need(type(offset) in (int, float) and math.isfinite(offset) and -18 <= offset <= 8, 'music.offset_db must be -18..8')
    loop = bool(selected.get('loop', False))
    inputs = {'engine': ENGINE, 'implementation': digest({
                  'pipeline': sha(ROOT/'scripts/music_pipeline.py'),
                  'mixer': sha(ROOT/'scripts/mix_background.py'),
              }),
              'narration': bundle['audio_hash'], 'duration': bundle['duration'],
              'source': sha(source), 'license': sha(license_path), 'gap_db': gap,
              'offset_db': offset, 'loop': loop}
    return {'identity': digest(inputs), 'inputs': inputs, 'source': source,
            'license': license_data, 'candidate': selected['id'], 'loop': loop}


def prepare(p, bundle):
    from mix_background import decode, mix, encode_wav, RATE
    s = spec(p, bundle)
    if s is None:
        return None
    out = p.path/'.history'/('music-'+s['identity'][:24])
    manifest = out/'manifest.json'
    if manifest.exists():
        r = read(manifest)
        need(r['identity'] == s['identity'], 'Music cache identity mismatch')
        need(all(sha(out/name) == h for name, h in r['outputs'].items()), 'Music cache damaged; preserve it and investigate')
    else:
        # Failed partial generations never overwrite existing history.
        if out.exists(): out = out.with_name(out.name+'-'+stamp())
        out.mkdir(parents=True)
        voice = decode(p.file(bundle['audio']))
        source = decode_music(s['source'], len(voice)/RATE, s['loop'])
        mixed, bed, metrics = mix(voice, source, s['inputs']['gap_db'], s['inputs']['offset_db'])
        encode_wav(out/'soundtrack.wav', mixed)
        # Store a true zero-offset bed for the live control; offset is applied exactly once.
        _, base, base_metrics = mix(voice, source, s['inputs']['gap_db'], 0)
        base /= base_metrics['music_headroom_scale']
        encode_wav(out/'base-bed.wav', base, codec='pcm_f32le')
        encode_wav(out/'music-bed.wav', bed)
        r = {'identity': s['identity'], 'inputs': s['inputs'], 'metrics': metrics,
             'license': s['license'], 'voice_peak': float(np.abs(voice).max()),
             'base_peak': float(np.abs(base).max()),
             'outputs': {f.name: sha(f) for f in out.glob('*.wav')}}
        (out/'ATTRIBUTION.txt').write_text(s['license']['attribution']+'\n', encoding='utf-8')
        write(out/'manifest.json', r)
    record = {**r, 'dir': out.relative_to(p.path).as_posix(), 'candidate': s['candidate'], 'loop': s['loop']}
    p.state['music_mix'] = record
    p.save('music_prepared', identity=r['identity'])
    return record


def approved(p, record):
    a = p.state.get('music_approval', {})
    return a.get('identity') == record['identity'] and a.get('soundtrack_hash') == record['outputs']['soundtrack.wav']


def audio_path(p, bundle, record):
    return p.file(record['dir']+'/soundtrack.wav') if record else p.file(bundle['audio'])


def approve(p, args):
    record = prepare(p, compose_audio(p, True))
    need(record is not None, 'No music configured')
    need(args.evidence.strip(), 'Record actual music listening approval')
    need(args.review_hash == record['identity'], 'Use the exact music identity from status/draft manifest')
    a = {'identity': record['identity'], 'soundtrack_hash': record['outputs']['soundtrack.wav'], 'evidence': args.evidence, 'at': stamp()}
    write(p.path/'.history'/('music-approval-'+stamp()+'.json'), a)
    p.state['music_approval'] = a
    p.save('music_approved', identity=record['identity'])


def status(p):
    if not p.data.get('music') or p.data['music'].get('enabled', True) is False:
        return {'state': 'disabled'}
    try:
        s = spec(p, compose_audio(p, True))
        record = p.state.get('music_mix', {})
        valid = record.get('identity') == s['identity'] and all(sha(p.file(record['dir']+'/'+name)) == h for name,h in record['outputs'].items())
        return {'state': ('approved' if approved(p, record) else 'needs listening') if valid else 'missing/stale', 'identity': s['identity']}
    except (ValueError, KeyError, FileNotFoundError) as e:
        return {'state': 'blocked', 'reason': str(e)}


def audition(p, bundle, output):
    """Build one review WAV per candidate without changing the selected track."""
    from mix_background import decode, encode_wav, mix, RATE
    result = music_candidates(p)
    out = p.file(output)
    need(not out.exists(), 'Music audition output already exists; use a new version')
    out.mkdir(parents=True)
    voice = decode(p.file(bundle['audio']))
    original = dict(p.data.get('music') or {})
    rows, manifest = [], {'scope': 'candidate audition; not an export approval',
                          'voice': bundle['audio'], 'voice_hash': bundle['audio_hash'],
                          'duration': bundle['duration'], 'candidates': []}
    try:
        for candidate in result['candidates']:
            config = p.data['music']
            config['source'], config['license'] = candidate['source'], candidate['license']
            config['loop'], config['selected'] = bool(candidate.get('loop', False)), candidate['id']
            source = decode_music(p.file(candidate['source']), len(voice)/RATE, bool(candidate.get('loop', False)))
            mixed, music, metrics = mix(voice, source, config.get('gap_db', 24), config.get('offset_db', 0))
            # Audition is post-headroom, matching the actual export level.
            mixed = voice + music
            name = 'audition-' + candidate['id'] + '.wav'
            encode_wav(out / name, mixed)
            row = {'id': candidate['id'], 'title': candidate['title'], 'artist': candidate['artist'],
                   'file': (out / name).relative_to(p.path).as_posix(), 'source': candidate['source'],
                   'license': candidate['license'], 'loop': bool(candidate.get('loop', False)),
                   'metrics': metrics, 'output_hash': sha(out / name)}
            manifest['candidates'].append(row)
            rows.append(row)
    finally:
        p.data['music'] = original
    write(out / 'manifest.json', manifest)
    return {'dir': out.relative_to(p.path).as_posix(), 'candidates': rows,
            'next': 'Listen to each WAV, then run music-select with the chosen candidate id.'}


def export_check(target, record):
    import numpy as np
    from mix_background import decode, RATE
    decoded = decode(target)
    need(float(np.abs(decoded).max()) < 1, 'Encoded soundtrack clips')
    need(abs(len(decoded)/RATE-record['inputs']['duration']) < .15, 'Encoded soundtrack duration drift')


def make_mixer(p, out, video, bundle, record):
    def url(path): return quote(os.path.relpath(path, out).replace('\\', '/'), safe='/')
    from studio import run, ffmpeg
    poster=out/'mixer-poster.jpg'
    run([ffmpeg(),'-v','error','-y','-i',video,'-frames:v','1','-q:v','3',poster])
    data = {'title': p.data.get('title','当前视频'), 'duration': bundle['duration'],
            'width': p.data['profile']['width'], 'height': p.data['profile']['height'], 'poster': url(poster),
            'video': url(video), 'voice': url(p.file(bundle['audio'])),
            'music': url(p.file(record['dir']+'/base-bed.wav')),
            'offset': record['inputs']['offset_db'], 'gap': record['inputs']['gap_db'],
            'voicePeak': record['voice_peak'], 'basePeak': record['base_peak'],
            'identity': record['identity']}
    template = (ROOT/'assets/music-mixer.html').read_text(encoding='utf-8')
    (out/'mixer.html').write_text(template.replace('/*MIX_DATA*/', json.dumps(data, ensure_ascii=False).replace('</', '<\\/')), encoding='utf-8')

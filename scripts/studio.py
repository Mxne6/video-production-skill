"""Resumable HTML -> narrated MP4 production. Python 3.10+, no paid retries."""
from __future__ import annotations
import argparse, contextlib, hashlib, html, json, math, os, re, shutil, subprocess
import sys, time, unicodedata, urllib.request, uuid, wave
import getpass
from pathlib import Path
from language_profiles import (DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, default_voice_id,
                               estimate_narration_seconds, is_english, language_boost,
                               language_identity, normalize_language)
from video_templates import (VIDEO_MODES, VIDEO_PROFILE, VIDEO_TEMPLATES,
                             create_scene_files, new_scene_data, validate_visual_system)

VERSION = '1.4.0'
RENDER_LAYOUT_VERSION = 'body-padding-reset-v1'
ROOT = Path(__file__).resolve().parents[1]

def api_endpoint():
    endpoint = os.environ.get('MINIMAX_TTS_ENDPOINT','https://api.minimax.cn/v1/t2a_v2')
    need(endpoint in ['https://api.minimax.cn/v1/t2a_v2','https://api.minimaxi.com/v1/t2a_v2','https://api-bj.minimaxi.com/v1/t2a_v2','https://api.minimax.io/v1/t2a_v2'], 'Use an official MiniMax endpoint')
    return endpoint

def api_key(args):
    key = getpass.getpass('MiniMax API key (hidden): ') if getattr(args,'prompt_key',False) else os.environ.get('MINIMAX_API_KEY')
    need(key and key.strip(), 'MINIMAX_API_KEY is missing; use --prompt-key or process environment')
    return key.strip()

def voices(p, args):
    req = urllib.request.Request(api_endpoint().replace('/t2a_v2','/get_voice'), b'{"voice_type":"system"}',
                                 {'Content-Type':'application/json','Authorization':'Bearer '+api_key(args)})
    with urllib.request.urlopen(req, timeout=60) as response: data=json.loads(response.read())
    code=data.get('base_resp',{}).get('status_code')
    need(code == 0, 'MiniMax voice query failed; status_code='+str(code))
    rows=data.get('system_voice'); need(isinstance(rows,list), 'Unsupported voice response')
    target=p.path/'review'/('minimax-voices-'+stamp()+'.json')
    write(target, {'at':stamp(),'endpoint':api_endpoint().replace('/t2a_v2','/get_voice'),'system_voice':rows})
    print(json.dumps({'system_voice_count':len(rows),'saved':str(target)},ensure_ascii=False))

def validate_voice(voice):
    allowed={'voice_id','speed','vol','pitch','emotion','text_normalization','latex_read'}
    need(not set(voice)-allowed, 'Unknown voice_setting field')
    for name,lo,hi in [('speed',.5,2),('vol',0,10),('pitch',-12,12)]:
        value=voice.get(name, 0 if name=='pitch' else 1)
        need(type(value) in (int,float) and math.isfinite(value) and lo<=value<=hi and (name!='vol' or value>0), 'Invalid voice '+name)
        if name=='pitch': need(type(value) is int, 'voice pitch must be integer')
    # Official 2.8 documentation is inconsistent about fluent; do not enable it by default.
    if 'emotion' in voice: need(voice['emotion'] in ['happy','sad','angry','fearful','disgusted','surprised','calm'], 'Unsupported emotion for speech-2.8-hd')
    for name in ['text_normalization','latex_read']:
        if name in voice: need(type(voice[name]) is bool, name+' must be boolean')

def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def write(p, obj):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(p)

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def norm(s):
    return ''.join(c for c in s if not c.isspace() and unicodedata.category(c)[0] != 'P')

def need(ok, message):
    if not ok: raise ValueError(message)

def ffmpeg():
    if os.environ.get('FFMPEG'): return os.environ['FFMPEG']
    try:
        import imageio_ffmpeg
        bundled = imageio_ffmpeg.get_ffmpeg_exe()
        if bundled: return bundled
    except (ImportError, OSError, RuntimeError):
        pass
    found = shutil.which('ffmpeg')
    need(found, 'FFmpeg is unavailable; set FFMPEG or install imageio-ffmpeg')
    return found

def run(args):
    p = subprocess.run([str(a) for a in args], capture_output=True)
    need(p.returncode == 0, p.stderr.decode('utf-8', errors='replace')[-3500:])
    return p

def wav_duration(p):
    with wave.open(str(p), 'rb') as w: return w.getnframes() / w.getframerate()

def stamp():
    return time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8]

class Project:
    def __init__(self, path):
        self.path = Path(path).resolve(); self.data = read(self.path/'project.json')
        self.state = read(self.path/'state.json') if (self.path/'state.json').exists() else {'scripts':{}, 'attempts':{}, 'audio':{}}
        ids = [s['id'] for s in self.data['scenes']]
        need(ids and len(ids) == len(set(ids)), 'Scene IDs must be unique and nonempty')
        need(all(re.fullmatch(r'[a-zA-Z0-9_-]+', i) for i in ids), 'Unsafe scene ID')
        p = self.data['profile']
        need(p['width'] > 0 and p['height'] > 0 and p['width'] % 2 == 0 and p['height'] % 2 == 0 and 1 <= p['fps'] <= 60, 'Invalid video profile')
        self.language()
        need(all('language' not in scene for scene in self.data['scenes']), 'Scene language overrides are unsupported; create a separate target-language project')

    def language(self): return normalize_language(self.data.get('language'))

    def file(self, rel):
        p = (self.path / rel).resolve()
        need(p.is_relative_to(self.path), 'Project path escapes root: ' + str(rel))
        return p

    def save(self, event, **details):
        write(self.path/'state.json', self.state)
        with (self.path/'journal.jsonl').open('a', encoding='utf-8') as f:
            f.write(json.dumps({'at':stamp(), 'event':event, **details}, ensure_ascii=False)+'\n')

    def scenes(self, selected='all'):
        ids = selected.split(',')
        scenes = [s for s in self.data['scenes'] if selected == 'all' or s['id'] in ids]
        need(scenes and (selected == 'all' or len(scenes) == len(set(ids))), 'Unknown scene selection')
        return scenes

    def script_hash(self, s):
        claims = [c for c in self.data.get('claims', []) if c['id'] in s.get('claim_ids', [])]
        sources = {x['id']: x for x in self.data.get('sources', [])}
        deps = []
        for c in claims:
            need(c['source_id'] in sources and c.get('quote') and c.get('locator'), 'Claim needs source, quote and locator')
            src = sources[c['source_id']]
            deps.append([c, sha(self.file(src['path']))])
        need(len(claims) == len(set(s.get('claim_ids', []))), 'Unknown claim ID')
        classification=[s.get('content_kind'),s.get('nonfactual_reason')] if self.data.get('contract_version',1)>=2 or 'content_kind' in s else None
        historical = [s['narration'], deps, classification] if classification is not None else [s['narration'], deps]
        language = language_identity(self.language())
        return digest(historical if language is None else [*historical, language])

    def payload(self, s):
        voice = {**self.data['voice'], **s.get('voice', {})}
        validate_voice(voice)
        text = s['narration']
        need('<#' not in text, 'Keep pause controls in pauses, not narration')
        pauses=[]
        for item in s.get('pauses', []):
            need(('after' in item) != ('offset' in item), 'Pause needs either after or offset')
            if 'after' in item:
                need(isinstance(item['after'],str) and text.startswith(item['after']), 'Pause after must be exact narration prefix')
            pos=len(item['after']) if 'after' in item else item['offset']
            sec=item['seconds']
            need(type(pos) is int and 0<pos<len(text), 'Invalid pause offset')
            need(type(sec) in (int,float) and math.isfinite(sec) and .01<=sec<=99.99 and abs(sec*100-round(sec*100))<1e-8, 'Pause seconds need 0.01–99.99 and at most two decimals')
            pauses.append({'offset':pos,'seconds':sec})
        pauses.sort(key=lambda x:x['offset'])
        need(len({x['offset'] for x in pauses})==len(pauses), 'Duplicate pause offset')
        boundaries=[0]+[x['offset'] for x in pauses]+[len(text)]
        need(all(any(c.isalnum() for c in text[a:b]) for a,b in zip(boundaries,boundaries[1:])), 'Pause controls must have pronounceable text between them')
        for pause in reversed(pauses):
            pos = pause['offset']; sec = pause['seconds']
            need(isinstance(pos,int) and 0 < pos < len(s['narration']) and .01 <= sec <= 99.99, 'Invalid pause')
            text = text[:pos] + f'<#{sec:.2f}#>' + text[pos:]
        need(0 < len(text) < 10000, 'TTS text must be 1–9999 characters')
        tone=s.get('pronunciation', self.data.get('pronunciation', []))
        need(isinstance(tone,list) and all(isinstance(x,str) and '/' in x and all(x.split('/',1)) for x in tone), 'Pronunciation needs original/replacement rules')
        payload = {'model':'speech-2.8-hd', 'text':text, 'stream':False,
                'voice_setting':voice, 'language_boost':language_boost(self.language()),
                'audio_setting':{'sample_rate':44100, 'bitrate':256000, 'format':'mp3', 'channel':1},
                'subtitle_enable':True, 'subtitle_type':'word', 'output_format':'hex',
                'pronunciation_dict':{'tone':tone}}
        modify={**self.data.get('voice_modify',{}), **s.get('voice_modify',{})}
        need(not set(modify)-{'pitch','intensity','timbre','sound_effects'}, 'Unknown voice_modify field')
        for name in ['pitch','intensity','timbre']:
            if name in modify: need(type(modify[name]) is int and -100<=modify[name]<=100, 'Invalid voice_modify '+name)
        if 'sound_effects' in modify: need(modify['sound_effects'] in ['spacious_echo','auditorium_echo','lofi_telephone','robotic'], 'Unknown sound effect')
        if modify: payload['voice_modify']=modify
        return payload

    def audio_key(self, s):
        return digest([self.script_hash(s), self.payload(s)])

    def attempt(self, s, approved=False):
        a = self.state['attempts'].get(s['id'])
        need(a and a['key'] == self.audio_key(s), f"{s['id']}: missing/stale audio")
        for path, h in a['files'].items(): need(sha(self.file(path)) == h, 'Changed immutable attempt: '+path)
        need(a['mode'] == ('test' if self.data.get('test_mode') else 'final'), 'Test/audition audio is not production narration')
        if approved:
            need(self.state['audio'].get(s['id'], {}).get('fingerprint') == digest(a), s['id']+': audio needs listening approval')
        return a

    def visual_content_key(self, s):
        # Hash local visual dependency tree, not unrelated scene assets.
        seen = {}
        def visit(rel):
            p = self.file(rel)
            need(p.exists(), 'Missing visual dependency: '+rel)
            if rel in seen: return
            seen[rel] = sha(p)
            if p.suffix.lower() in ('.html','.css','.js','.mjs'):
                content = p.read_text(encoding='utf-8')
                for ref in re.findall(r'''(?:src|href)\s*=\s*["']([^"']+)["']|url\(\s*["']?([^)'"\s]+)''', content):
                    url = (ref[0] or ref[1]).split('#')[0].split('?')[0]
                    if not url or url.startswith('data:'): continue
                    need(not re.match(r'^(https?:)?//', url), 'Localize remote visual resources: '+url)
                    visit(str((p.parent/url).resolve().relative_to(self.path)))
        visit(s['html'])
        for dep in s.get('dependencies', []): visit(dep)
        for aid in s.get('assets', []):
            a = next((x for x in self.data.get('assets', []) if x['id'] == aid), None)
            need(a and a.get('status') == 'ready' and a.get('path'), 'Waiting for asset '+aid)
            visit(a['path'])
        historical = [seen, s.get('beats', []), self.data['profile'], self.data.get('test_mode', False), VERSION]
        language = language_identity(self.language())
        return digest(historical if language is None else [*historical, language])

    def visual_key(self, s):
        from production_contract import review_metadata
        return digest([self.visual_content_key(s), review_metadata(self, s)])

def normalize_timing(raw, unit):
    # Explicit supported forms; do not guess unit or spread sentence timestamps.
    need(unit in ('ms','s'), 'Unknown timing unit')
    need(isinstance(raw,(list,dict)), 'Unsupported timing schema')
    entries = raw if isinstance(raw, list) else raw.get('words', raw.get('subtitles'))
    need(isinstance(entries, list) and entries, 'Unsupported timing schema: inspect raw JSON, add an explicit adapter')
    result = []; factor = .001 if unit == 'ms' else 1
    for row in entries:
        need(isinstance(row,dict), 'Invalid timing entry')
        if 'timestamped_words' in row:
            result.extend(normalize_minimax_segment(row,unit)); continue
        if 'words' in row and isinstance(row['words'], list):
            result.extend(normalize_timing(row['words'], unit)); continue
        text = row.get('text', row.get('word'))
        start = row.get('start', row.get('start_time')); end = row.get('end', row.get('end_time'))
        need(isinstance(text, str) and isinstance(start, (int,float)) and isinstance(end, (int,float)), 'Invalid timing entry')
        result.append({'text':text, 'start':start*factor, 'end':end*factor})
    return result

def normalize_minimax_segment(segment, unit):
    # Observed live 2.8 schema: repeated source spans represent pronunciation pieces.
    text=segment['text']; origin=segment['text_begin']; end=segment['text_end']
    need(end-origin==len(text), 'Unsupported MiniMax source offset convention')
    groups=[]; factor=.001 if unit=='ms' else 1
    for w in segment['timestamped_words']:
        a,b=w['word_begin'],w['word_end']; start,stop=w['time_begin']*factor,w['time_end']*factor
        need(origin<=a<b<=end and text[a-origin:b-origin]==w['word'], 'MiniMax source span mismatch')
        need(math.isfinite(start) and math.isfinite(stop) and stop>start, 'Invalid MiniMax word timing')
        if groups and (a,b)==(groups[-1]['a'],groups[-1]['b']):
            need(start>=groups[-1]['end']-1e-6, 'Overlapping pronunciation pieces')
            groups[-1]['end']=stop
        else:
            need(not groups or (a>=groups[-1]['b'] and start>=groups[-1]['end']-1e-6), 'Unordered MiniMax words')
            groups.append({'a':a,'b':b,'text':w['word'],'start':start,'end':stop})
    need(groups, 'Missing MiniMax word timestamps')
    # Silent typography may be omitted by the provider; retain it without inventing time.
    def silent(gap):
        return all(c.isspace() or unicodedata.category(c).startswith('P') or c in '®™©' for c in gap)
    cursor=origin; output=[]
    for g in groups:
        gap=text[cursor-origin:g['a']-origin]
        need(silent(gap), 'MiniMax omitted spoken source text')
        if output: output[-1]['text']+=gap
        output.append({'text':('' if output else gap)+g['text'],'start':g['start'],'end':g['end']})
        cursor=g['b']
    gap=text[cursor-origin:]; need(silent(gap), 'MiniMax omitted trailing source text')
    output[-1]['text']+=gap
    return output

def validate_words(words, narration, duration, language=DEFAULT_LANGUAGE):
    source = ''.join(w['text'] for w in words)
    if is_english(language):
        need(source == narration, 'English timing text must preserve canonical narration exactly, including spaces and punctuation')
    else:
        need(norm(source) == norm(narration), 'Timing text differs from canonical narration; inspect pronunciation mapping/alignment')
    last = 0
    for w in words:
        need(math.isfinite(w['start']) and math.isfinite(w['end']) and w['start'] >= last-1e-6 and w['end'] > w['start'] and w['end'] <= duration+.06, 'Invalid, overlapping or out-of-range timing')
        last = w['end']

def validate_attempt_language(p, metadata):
    recorded, target = metadata.get('target_language'), p.language()
    if target == DEFAULT_LANGUAGE: need(recorded in (None, DEFAULT_LANGUAGE), 'Saved attempt target language differs from this project')
    else: need(recorded == target, 'English saved attempt must record the exact target language')


def finish_attempt(p, s, folder, unit, mode):
    need(not (folder/'completion.json').exists() and not any(a.get('dir')==folder.relative_to(p.path).as_posix() for a in p.state['attempts'].values()), 'Cannot overwrite a completed audio attempt')
    need(mode!='test' or p.data.get('test_mode'), 'Test audio cannot enter a production project')
    transport_path = folder/'transport.json'
    if p.language() != DEFAULT_LANGUAGE:
        need(transport_path.exists(), 'English saved attempt must record the exact target language')
        validate_attempt_language(p, read(transport_path))
    elif transport_path.exists():
        validate_attempt_language(p, read(transport_path))
    run([ffmpeg(),'-v','error','-y','-i',folder/'audio.mp3','-ar','48000','-ac','1','-c:a','pcm_s16le',folder/'audio.wav'])
    duration = wav_duration(folder/'audio.wav')
    words = normalize_timing(read(folder/'timing.raw.json'), unit)
    validate_words(words, s['narration'], duration, p.language())
    write(folder/'words.json', words)
    completion = {'mode':mode,'unit':unit,'request_sha256':sha(folder/'request.json')}
    if p.language() != DEFAULT_LANGUAGE: completion['target_language'] = p.language()
    write(folder/'completion.json', completion)
    rel = folder.relative_to(p.path).as_posix()
    a = {'key':p.audio_key(s), 'mode':mode, 'dir':rel, 'duration':duration,
         'files':{f.relative_to(p.path).as_posix():sha(f) for f in folder.iterdir() if f.is_file()}}
    p.state['attempts'][s['id']] = a
    p.save('audio_attempt', scene=s['id'], attempt=rel, mode=mode)
    return a

def selected_approval(p, args):
    need(args.evidence.strip(), 'Record the user approval text and task/message reference')
    from production_contract import content_check
    for s in p.scenes(args.scenes):
        content_check(p,s)
        p.state['scripts'][s['id']] = {'hash':p.script_hash(s), 'evidence':args.evidence, 'at':stamp()}
    write(p.path/'.history'/('script-approval-'+stamp()+'.json'), p.state['scripts'])
    p.save('script_approved', scenes=args.scenes, evidence=args.evidence)

def tts(p, args):
    scenes = p.scenes(args.scenes)
    need(len(scenes) == 1, 'One explicit TTS request at a time; select one semantic segment')
    s = scenes[0]; payload = p.payload(s)
    if args.send:
        from production_contract import duration_check, content_check
        duration_check(p)
        content_check(p, s)
        need(p.state['scripts'].get(s['id'], {}).get('hash') == p.script_hash(s), 'Approve this script revision before synthesis')
        need(not p.data.get('test_mode'), 'Test project cannot send paid synthesis')
        need(payload['voice_setting'].get('voice_id'), 'Set a verified MiniMax voice_id')
        endpoint=api_endpoint(); key=api_key(args)
    folder = p.path/'.history'/('tts-'+s['id']+'-'+stamp()); folder.mkdir(parents=True)
    write(folder/'request.json', payload)
    if not args.send:
        print('Prepared only: '+str(folder/'request.json')); return
    transport = {'endpoint':endpoint,'mode':args.mode or 'final','unit':args.unit or 'ms','sent_at':stamp()}
    if p.language() != DEFAULT_LANGUAGE: transport['target_language'] = p.language()
    write(folder/'transport.json', transport)
    p.save('tts_sent_no_automatic_retry', scene=s['id'], request=str(folder.relative_to(p.path)))
    req = urllib.request.Request(endpoint, json.dumps(payload).encode(), {'Content-Type':'application/json','Authorization':'Bearer '+key})
    try:
        with urllib.request.urlopen(req, timeout=240) as response: body=response.read()
        (folder/'response.raw.json').write_bytes(body); data=json.loads(body)
        download_saved_result(folder)
        finish_attempt(p,s,folder,args.unit or 'ms',args.mode or 'final')
        print(folder)
    except Exception:
        p.save('tts_incomplete_check_saved_attempt_before_retry', folder=str(folder.relative_to(p.path)))
        raise

def download_saved_result(folder):
    data=read(folder/'response.raw.json')
    need(data.get('base_resp',{}).get('status_code') == 0, 'MiniMax returned an error; inspect saved response')
    d=data.get('data'); need(isinstance(d,dict), 'MiniMax response has no data')
    audio=folder/'audio.mp3'
    if not audio.exists():
        decoded=bytes.fromhex(d['audio']); need(decoded, 'Empty MiniMax audio')
        audio.write_bytes(decoded)
    if not (folder/'timing.raw.json').exists():
        url=d.get('subtitle_file')
        need(isinstance(url,str) and url.startswith('https://'), 'No subtitle_file: inspect saved response; do not regenerate paid audio')
        with urllib.request.urlopen(url, timeout=60) as response: body=response.read()
        json.loads(body)  # Do not cache a truncated or non-JSON download.
        (folder/'timing.raw.json').write_bytes(body)

def saved_attempt_metadata(p, folder, args):
    rel=folder.relative_to(p.path).as_posix()
    need(not (folder/'completion.json').exists() and not (folder/'attachment.json').exists()
         and not any(a.get('dir')==rel for a in p.state['attempts'].values())
         and not (folder/'audio.wav').exists() and not (folder/'words.json').exists(),
         'Attempt already materialized; preserve history and import a fresh copy')
    metadata=read(folder/'transport.json')
    mode,unit=metadata.get('mode'),metadata.get('unit')
    need(mode in ('test','audition','final') and unit in ('ms','s'), 'Missing original attempt mode/unit')
    need(not getattr(args,'mode',None) or args.mode==mode, 'Cannot relabel original attempt mode')
    need(not getattr(args,'unit',None) or args.unit==unit, 'Cannot reinterpret original timing unit')
    need(mode!='test' or p.data.get('test_mode'), 'Test audio cannot enter a production project')
    validate_attempt_language(p, metadata)
    return metadata

def recover(p,args):
    scenes=p.scenes(args.scenes); need(len(scenes)==1, 'Select one scene')
    s=scenes[0]; folder=p.file(args.attempt)
    need(read(folder/'request.json')==p.payload(s), 'Saved request does not match current narration/settings')
    metadata=saved_attempt_metadata(p,folder,args)
    download_saved_result(folder)  # GET only, no key, no synthesis call.
    finish_attempt(p,s,folder,metadata['unit'],metadata['mode'])
    print(folder)

def attach(p, args):
    scenes=p.scenes(args.scenes); need(len(scenes)==1, 'Select one scene')
    s=scenes[0]; source=p.file(args.attempt)
    need(read(source/'request.json')==p.payload(s), 'Saved request does not match current narration/settings')
    # Imports are immutable new versions. Validate the source mode before any copy or conversion.
    metadata=read(source/'transport.json')
    mode,unit=metadata.get('mode'),metadata.get('unit')
    need(mode in ('test','audition','final') and unit in ('ms','s'), 'Missing original attempt mode/unit')
    need(not getattr(args,'mode',None) or args.mode==mode, 'Cannot relabel original attempt mode')
    need(not getattr(args,'unit',None) or args.unit==unit, 'Cannot reinterpret original timing unit')
    need(mode!='test' or p.data.get('test_mode'), 'Test audio cannot enter a production project')
    validate_attempt_language(p, metadata)
    need(not (source/'attachment.json').exists()
         and not any(a.get('dir')==source.relative_to(p.path).as_posix() for a in p.state['attempts'].values()),
         'Attempt already attached; preserve its immutable history')
    source_hash=digest({f.name:sha(f) for f in source.iterdir() if f.is_file()})
    need(not any(a.get('import_source_hash')==source_hash for a in p.state['attempts'].values()),
         'Source already imported; reuse current attempt')
    folder=p.path/'.history'/('import-'+s['id']+'-'+stamp())
    folder.mkdir(parents=True)
    for name in ('request.json','transport.json','audio.mp3','timing.raw.json','response.raw.json'):
        if (source/name).exists(): shutil.copyfile(source/name,folder/name)
    write(folder/'attachment.json', {'source':source.relative_to(p.path).as_posix(),'source_hash':source_hash})
    a=finish_attempt(p,s,folder,unit,mode)
    a['import_source_hash']=source_hash
    p.save('audio_imported',scene=s['id'],source=source.relative_to(p.path).as_posix())

def compose_audio(p, approved=False):
    fps=p.data['profile']['fps']; timeline=[]; frames=0
    for s in p.scenes():
        a=p.attempt(s,approved)
        count=math.ceil((a['duration']+s.get('tail_seconds',.25))*fps)
        duration=count/fps
        words=read(p.file(a['dir']+'/words.json'))
        boundaries={0:0}; n=0
        for w in words:
            n += len(w['text']) if is_english(p.language()) else len(norm(w['text'])); boundaries[n]=w['end']
        beats=[]
        for b in s.get('beats',[]):
            prefix=b['after']; need(s['narration'].startswith(prefix), 'Beat after must be exact narration prefix')
            idx = len(prefix) if is_english(p.language()) else len(norm(prefix)); need(idx in boundaries, 'Beat falls inside timestamp token; choose real boundary')
            beats.append({'id':b['id'], 'at':boundaries[idx]})
        timeline.append({'id':s['id'], 'start':frames/fps,'duration':duration,'frames':count,'audio':a['dir']+'/audio.wav', 'attempt':digest(a),'html':s['html'],'beats':beats})
        frames+=count
    key=digest(timeline); out=p.path/'.history'/('mix-'+key[:20]); out.mkdir(parents=True,exist_ok=True)
    wav=out/'narration.wav'
    expected_frames=sum(round(t['duration']*48000) for t in timeline)
    def valid_cached_wav(path):
        try:
            with wave.open(str(path),'rb') as source:
                return (source.getnchannels()==1 and source.getsampwidth()==2
                        and source.getframerate()==48000 and source.getnframes()==expected_frames)
        except (OSError, EOFError, wave.Error):
            return False
    if not wav.exists():
        partial=out/('.narration-'+uuid.uuid4().hex+'.wav')
        try:
            with wave.open(str(partial),'wb') as target:
                target.setparams((1,2,48000,0,'NONE','not compressed'))
                for t in timeline:
                    samples=round(t['duration']*48000)
                    with wave.open(str(p.file(t['audio'])),'rb') as source:
                        audio=source.readframes(source.getnframes())
                    need(len(audio)<=samples*2, 'Audio would be truncated')
                    target.writeframes(audio+b'\0'*(samples*2-len(audio)))
            need(valid_cached_wav(partial), 'Assembled narration cache is invalid')
            partial.replace(wav)
        finally:
            if partial.exists(): partial.unlink()
    else:
        need(valid_cached_wav(wav), 'Damaged cached narration; preserve it and investigate')
    bundle={'timeline':timeline,'audio':wav.relative_to(p.path).as_posix(),'audio_hash':sha(wav),'duration':frames/fps,'key':key}
    write(out/'bundle.json', bundle)
    return bundle

def approve_audio(p,args):
    bundle=compose_audio(p)
    need(args.evidence.strip(), 'Record listening approval for the exact full audio/excerpt')
    need(args.review_hash == bundle['audio_hash'], 'Approval must name current assembled WAV SHA256; run preview first')
    for s in p.scenes(args.scenes):
        a=p.attempt(s)
        p.state['audio'][s['id']]={'fingerprint':digest(a),'evidence':args.evidence,'mix_hash':args.review_hash,'at':stamp()}
    write(p.path/'.history'/('audio-approval-'+stamp()+'.json'),p.state['audio'])
    p.save('audio_approved',scenes=args.scenes,evidence=args.evidence)

def split_captions(s, words, duration, protected, language=DEFAULT_LANGUAGE):
    language = normalize_language(language); validate_words(words,s['narration'],duration,language)
    phrases=s.get('caption_phrases', []); need(phrases and ''.join(phrases)==s['narration'], 'caption_phrases must reconstruct narration exactly, including punctuation')
    text=s['narration']; boundaries={0}; cursor=0
    if is_english(language):
        from caption_language import english_boundaries
        boundaries=english_boundaries(text, protected)
    else:
        import jieba
        jieba.setLogLevel(40)
        for term in protected: jieba.add_word(term, freq=10000000)
        for token in jieba.cut(text,HMM=False): cursor+=len(token); boundaries.add(cursor)
    cuts=[]; cursor=0
    for phrase in phrases[:-1]: cursor+=len(phrase); cuts.append(cursor)
    for cut in cuts:
        need(cut in boundaries, f'Caption splits a linguistic word at {cut}; revise phrases')
        for term in ([] if is_english(language) else protected+re.findall(r'[A-Za-z0-9][A-Za-z0-9._+%/-]*',text)):
            for m in re.finditer(re.escape(term),text): need(not m.start()<cut<m.end(), 'Caption splits protected term: '+term)
    offsets={}; n=0
    for w in words:
        k=len(w['text']) if is_english(language) else len(norm(w['text']))
        if not k: continue
        offsets.setdefault(n,{})['start']=w['start']; n+=k
        offsets.setdefault(n,{})['end']=w['end']
    result=[]; n=0
    for phrase in phrases:
        end=n+(len(phrase) if is_english(language) else len(norm(phrase)))
        need(n in offsets and 'start' in offsets[n] and end in offsets and 'end' in offsets[end], 'Caption boundary inside provider token; cannot invent timings')
        need('\n' not in phrase and '\r' not in phrase and end>n, 'Empty/multiline caption')
        result.append({'text':phrase,'start':offsets[n]['start'],'end':offsets[end]['end']}); n=end
    return result

def captions(p):
    bundle=compose_audio(p,True); cues=[]
    for s,t in zip(p.scenes(),bundle['timeline']):
        a=p.attempt(s,True); words=read(p.file(a['dir']+'/words.json'))
        for i,c in enumerate(split_captions(s,words,a['duration'],p.data.get('protected_terms',[]),p.language()),1):
            cues.append({**c,'id':f"{s['id']}-{i:03d}",'scene':s['id'],'start':c['start']+t['start'],'end':c['end']+t['start']})
    result={'bundle':bundle,'cues':cues,'protected_terms':p.data.get('protected_terms',[])}
    if p.language() != DEFAULT_LANGUAGE: result['language']=p.language()
    path=p.path/'.history'/('captions-'+digest(result)[:20]+'.json'); write(path,result)
    p.state['captions']=path.relative_to(p.path).as_posix(); p.save('captions_generated',artifact=p.state['captions'])
    return result

def current_captions(p):
    need(p.state.get('captions'), 'Generate captions after audio approval')
    c=read(p.file(p.state['captions'])); bundle=compose_audio(p,True)
    need(c['bundle']==bundle,'Captions stale: audio/order/duration changed')
    need(c.get('protected_terms',[])==p.data.get('protected_terms',[]),'Protected terms changed; regenerate captions')
    need(c.get('language', DEFAULT_LANGUAGE)==p.language(), 'Target language changed; regenerate captions')
    for s in p.scenes():
        need(''.join(x['text'] for x in c['cues'] if x['scene']==s['id'])==s['narration'], 'Stale caption wording')
        need([x['text'] for x in c['cues'] if x['scene']==s['id']]==s['caption_phrases'], 'Caption segmentation changed; regenerate')
    return c

def review_identity(p,c):
    return digest([c, [p.visual_key(s) for s in p.scenes()],sha(ROOT/'assets/player.html')])

def cue_review_keys(p,c):
    keys={}
    for s,t in zip(p.scenes(),c['bundle']['timeline']):
        visual=p.visual_key(s)
        for cue in (x for x in c['cues'] if x['scene']==s['id']):
            keys[cue['id']]=digest([t['attempt'],visual,cue['text'],round(cue['start']-t['start'],6),round(cue['end']-t['start'],6)])
    return keys

def preview(p, args):
    if args.captions:
        c=current_captions(p); identity=review_identity(p,c)
    else: c={'bundle':compose_audio(p),'cues':[]}; identity=digest(c)
    out=p.path/'review'; out.mkdir(exist_ok=True)
    data={**c,'identity':identity,'profile':p.data['profile'],'caption_css':caption_css(p.data['profile']),'test_mode':p.data.get('test_mode',False)}
    data['cue_keys']=cue_review_keys(p,c) if args.captions else {}
    data['initial_marks']={}
    old=p.state.get('qa')
    if old and p.file(old['path']).exists() and sha(p.file(old['path']))==old['hash']:
        previous=read(p.file(old['path']))
        by_key={previous.get('cue_keys',{}).get(k):v for k,v in previous['cues'].items()}
        data['initial_marks']={k:by_key[h] for k,h in data['cue_keys'].items() if h in by_key}
    data['bundle']=json.loads(json.dumps(c['bundle']))
    data['bundle']['audio']='../'+data['bundle']['audio']
    for t in data['bundle']['timeline']: t['html']='../'+t['html']
    template=(ROOT/'assets/player.html').read_text(encoding='utf-8')
    (out/'index.html').write_text(template.replace('/*PROJECT_DATA*/',json.dumps(data,ensure_ascii=False).replace('</','<\\/')),encoding='utf-8')
    print(json.dumps({'preview':str(out/'index.html'),'audio':str(p.file(c['bundle']['audio'])),'audio_sha256':c['bundle']['audio_hash'],'identity':identity},ensure_ascii=False,indent=2))

def qa_import(p,args):
    c=current_captions(p); report=read(args.report)
    need(report['identity']==review_identity(p,c), 'QA report refers to different audio, captions or visuals')
    need(report.get('cue_keys')==cue_review_keys(p,c), 'QA cue dependencies differ')
    need(set(report['cues'])=={x['id'] for x in c['cues']}, 'QA must cover every cue')
    need(all(x.get('status')=='pass' for x in report['cues'].values()), 'Unresolved caption QA issues')
    need(report.get('reviewer') and report.get('listened') is True, 'Need named listening reviewer')
    path=p.path/'.history'/('qa-'+stamp()+'.json'); write(path,report)
    p.state['qa']={'path':path.relative_to(p.path).as_posix(),'hash':sha(path),'identity':report['identity']}; p.save('qa_imported')

def music_candidates(p):
    import music_pipeline
    print(json.dumps(music_pipeline.music_candidates(p),ensure_ascii=False,indent=2))

def music_select(p,args):
    import music_pipeline
    need(not (args.candidate_id and args.random_select),'Use either --candidate-id or --random, not both')
    print(json.dumps(music_pipeline.music_select(p,args.candidate_id,args.evidence,
                                                 'random' if args.random_select else None),ensure_ascii=False,indent=2))

def music_audition(p,args):
    import music_pipeline
    output=args.output or ('review/music-audition-'+stamp())
    print(json.dumps(music_pipeline.audition(p,compose_audio(p),output),ensure_ascii=False,indent=2))

def browser_start(pw):
    kwargs={'headless':True,'args':['--allow-file-access-from-files']}
    if os.environ.get('VIDEO_CHROME'): kwargs['executable_path']=os.environ['VIDEO_CHROME']
    return pw.chromium.launch(**kwargs)

def caption_css(profile):
    px = profile.get('caption_px', 48)
    return ('#vp-caption{position:fixed;left:8%;right:8%;bottom:5%;text-align:center;'
            'z-index:2147483646;white-space:nowrap;pointer-events:none}'
            '#vp-caption span{display:inline-block;max-width:100%;padding:.15em .5em;'
            'color:white;background:rgba(0,0,0,.82);font:500 '+str(px)+'px/1.4 '
            '"Microsoft YaHei",sans-serif}')

def render(p,args):
    from playwright.sync_api import sync_playwright
    c=current_captions(p); identity=review_identity(p,c)
    from production_contract import duration_check, production_gate
    duration_result=duration_check(p,c['bundle']['duration'])
    if not args.draft: production_gate(p)
    from music_pipeline import prepare, approved, audio_path
    music = prepare(p, c['bundle'])
    if music and not args.draft: need(approved(p, music), 'Music mix needs approval: render --draft, then approve-music with its identity')
    soundtrack = audio_path(p, c['bundle'], music)
    if not args.draft:
        qa=p.state.get('qa',{})
        need(qa.get('identity')==identity and sha(p.file(qa['path']))==qa['hash'], 'Complete current audible caption QA before final export')
    profile=p.data['profile']; w,h,fps=profile['width'],profile['height'],profile['fps']
    out=p.path/'renders'; out.mkdir(exist_ok=True); clips=[]; reused=[]; layout=[]
    with sync_playwright() as pw:
        browser=browser_start(pw)
        try:
            for s,t in zip(p.scenes(),c['bundle']['timeline']):
                local=[{**x,'start':round(x['start']-t['start'],9),'end':round(x['end']-t['start'],9)} for x in c['cues'] if x['scene']==s['id']]
                key=digest([p.visual_content_key(s),local,t['duration'],t['beats'],args.draft,RENDER_LAYOUT_VERSION])
                clip=out/(s['id']+'-'+key[:20]+'.mp4'); clips.append(clip)
                proof=clip.with_suffix('.qa.json')
                if clip.exists() and proof.exists() and read(proof).get('video_hash')==sha(clip):
                    reused.append(s['id']); layout.extend(read(proof)['layout']); continue
                page=browser.new_page(viewport={'width':w,'height':h},device_scale_factor=1)
                errors=[]; page.on('pageerror',lambda e:errors.append(str(e)))
                page.route(re.compile(r'^https?://'),lambda route:route.abort())
                page.goto(p.file(s['html']).as_uri()); page.evaluate('document.fonts.ready')
                page.evaluate('''async () => { await Promise.all([...document.images].map(i=>i.decode())); if(typeof window.renderAt!=='function') throw Error('Missing renderAt'); }''')
                page.add_style_tag(content='*{animation:none!important;transition:none!important}html,body{margin:0!important;padding:0!important;overflow:hidden!important}'+caption_css(profile)+'#vp-mark{position:fixed;top:12px;right:16px;z-index:2147483647;color:#fff;background:#222;padding:8px;font:18px sans-serif}')
                page.evaluate('''label=>{let d=document.createElement('div');d.id='vp-caption';d.innerHTML='<span></span>';document.body.append(d);if(label){let m=document.createElement('div');m.id='vp-mark';m.textContent=label;document.body.append(m)}}''', '测试音轨 · 非正式旁白' if p.data.get('test_mode') else ('审核版' if args.draft else ''))
                checks=[]
                def seek(sec,caption):
                    page.evaluate('''async o=>{window.productionBeats=o.beats;await window.renderAt(o.t,o.duration);let e=document.querySelector('#vp-caption span');e.textContent=o.caption;e.style.visibility=o.caption?'visible':'hidden';}''',{'t':sec,'duration':t['duration'],'caption':caption,'beats':t['beats']})
                for cue in local:
                    seek((cue['start']+cue['end'])/2,cue['text'])
                    info=page.evaluate('''()=>{let e=document.querySelector('#vp-caption span'),r=e.getBoundingClientRect(),safe=document.querySelector('#vp-caption').getBoundingClientRect();let overlaps=[...document.querySelectorAll('[data-safe-check]')].filter(x=>{let q=x.getBoundingClientRect();return q.bottom>safe.top&&q.top<safe.bottom&&q.left<safe.right&&q.right>safe.left}).map(x=>x.textContent);return {width:e.scrollWidth,available:safe.width,overflow:e.scrollWidth>safe.width||r.height>parseFloat(getComputedStyle(e).lineHeight)*1.5,overlaps}}''')
                    need(not info['overflow'] and not info['overlaps'], 'Caption overflow/visual collision: '+cue['text'])
                    checks.append({'id':cue['id'],**info})
                temp=clip.with_suffix('.partial.mp4'); log=clip.with_suffix('.ffmpeg.log')
                with log.open('wb') as stderr:
                    proc=subprocess.Popen([ffmpeg(),'-v','error','-y','-f','image2pipe','-vcodec','png','-framerate',str(fps),'-i','pipe:0','-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(temp)],stdin=subprocess.PIPE,stderr=stderr)
                    try:
                        for frame in range(t['frames']):
                            sec=frame/fps; cue=next((x['text'] for x in local if x['start']<=sec<x['end']),'')
                            seek(sec,cue)
                            data=page.screenshot(type='png'); proc.stdin.write(data)
                            if frame in {0,t['frames']//2,t['frames']-1}: (out/f"{s['id']}-{key[:8]}-{frame:05d}.png").write_bytes(data)
                        proc.stdin.close(); code=proc.wait()
                        need(code==0, 'Frame encode failed: '+log.read_text(errors='replace'))
                    except Exception:
                        proc.kill(); proc.wait(); raise
                need(not errors,'Browser error: '+'; '.join(errors))
                temp.replace(clip); page.close(); layout.extend(checks)
                write(proof,{'video_hash':sha(clip),'layout':checks})
                print('Rendered '+s['id'],flush=True)
        finally: browser.close()
    # Concat a list of generated safe basenames, avoiding shell quoting/path issues.
    listing=out/'concat.txt'; listing.write_text(''.join("file '"+x.name+"'\n" for x in clips),encoding='utf-8')
    final_dir=p.path/'exports'/stamp(); final_dir.mkdir(parents=True)
    target=final_dir/('TEST-video.mp4' if p.data.get('test_mode') else ('draft.mp4' if args.draft else 'video.mp4'))
    run([ffmpeg(),'-v','error','-y','-f','concat','-safe','0','-i',listing,'-i',soundtrack,'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart',target])
    run([ffmpeg(),'-v','error','-i',target,'-map','0:v:0','-map','0:a:0','-f','null','-'])
    # Decode the exported audio and count decoded frames, not just process success.
    check=final_dir/'decoded-audio.wav'; run([ffmpeg(),'-v','error','-y','-i',target,'-vn','-ar','48000','-ac','1',check])
    need(abs(wav_duration(check)-c['bundle']['duration'])<.15,'Export audio duration drift')
    counted=run([ffmpeg(),'-v','error','-i',target,'-map','0:v:0','-an','-progress','pipe:1','-f','null','-']).stdout.decode()
    frames=int(re.findall(r'frame=(\d+)',counted)[-1]); need(frames==sum(t['frames'] for t in c['bundle']['timeline']),'Export frame count drift')
    import imageio_ffmpeg
    reader=imageio_ffmpeg.read_frames(str(target))
    try: metadata=next(reader)
    finally: reader.close()
    need(tuple(metadata['size'])==(w,h) and abs(metadata['fps']-fps)<.01,'Export dimensions/fps differ')
    duration_result=duration_check(p,metadata['duration'])
    check.unlink()
    def tc(n):
        ms=round(n*1000); hh,ms=divmod(ms,3600000); mm,ms=divmod(ms,60000); ss,ms=divmod(ms,1000)
        return f'{hh:02}:{mm:02}:{ss:02},{ms:03}'
    (final_dir/'captions.srt').write_text('\n\n'.join(f"{i}\n{tc(x['start'])} --> {tc(x['end'])}\n{x['text']}" for i,x in enumerate(c['cues'],1))+'\n',encoding='utf-8')
    shutil.copyfile(p.file(c['bundle']['audio']),final_dir/'narration.wav')
    write(final_dir/'manifest.json',{'identity':identity,'video_hash':sha(target),'profile':profile,'language':p.language(),'duration':c['bundle']['duration'],'duration_check':duration_result,'container_duration':metadata['duration'],'frames':frames,'reused_scenes':reused,'layout':layout,'test_mode':p.data.get('test_mode',False),'draft':args.draft,'engine':VERSION,'ffmpeg':run([ffmpeg(),'-version']).stdout.decode().splitlines()[0]})
    if music:
        shutil.copyfile(soundtrack, final_dir/'soundtrack.wav')
        shutil.copyfile(p.file(music['dir']+'/ATTRIBUTION.txt'), final_dir/'ATTRIBUTION.txt')
        from music_pipeline import export_check, make_mixer
        export_check(target, music)
        if args.draft: make_mixer(p, final_dir, target, c['bundle'], music)
    manifest=read(final_dir/'manifest.json')
    manifest.update(soundtrack_hash=sha(soundtrack), music=music, final_identity=digest([identity, music['identity'] if music else None, p.data.get('duration')]))
    write(final_dir/'manifest.json', manifest)
    record_key='draft_export' if args.draft else 'export'
    p.state[record_key]={'path':str(target.relative_to(p.path)), 'hash':sha(target), 'identity':manifest['final_identity'], 'draft':args.draft}
    p.save('draft_exported' if args.draft else 'exported',path=str(target.relative_to(p.path)),reused=reused)
    print(target)

def export_states(p,music_state):
    export_state=p.state.get('export', {}).copy()
    draft_state=p.state.get('draft_export', {}).copy()
    if export_state.get('draft'):
        if not draft_state: draft_state=export_state
        export_state={}
    expected=None
    try:
        expected=digest([review_identity(p,current_captions(p)),music_state.get('identity'),p.data.get('duration')])
    except (ValueError,KeyError,FileNotFoundError):
        pass
    for state in (export_state,draft_state):
        if state:
            try:
                state['current']=expected is not None and state.get('identity')==expected and sha(p.file(state['path']))==state.get('hash')
            except (ValueError,KeyError,FileNotFoundError):
                state['current']=False
    return export_state,draft_state

def status(p):
    result=[]
    for s in p.scenes():
        row={'id':s['id'],'script_approved':p.state['scripts'].get(s['id'],{}).get('hash')==p.script_hash(s)}
        for kind,fn in [('audio',lambda:p.attempt(s,True)),('visual',lambda:p.visual_key(s))]:
            try: fn(); row[kind]='ready'
            except (ValueError,FileNotFoundError) as e: row[kind]=str(e)
        estimate=estimate_narration_seconds(s['narration'],p.language())
        if is_english(p.language()):
            pauses=sum(item.get('seconds', 0) for item in s.get('pauses', [])) + s.get('tail_seconds', .25)
            estimate=[round(value+pauses,1) for value in estimate]
        row['estimate_seconds']=estimate
        result.append(row)
    try:
        c=current_captions(p); caption_state='ready'; qa_state='ready' if p.state.get('qa',{}).get('identity')==review_identity(p,c) else 'needs review (unchanged cue checks retained)'
    except (ValueError,FileNotFoundError) as e: caption_state=str(e); qa_state='not ready'
    from music_pipeline import status as music_status
    music_state=music_status(p)
    export_state,draft_state=export_states(p,music_state)
    from production_contract import duration_check, production_gate
    try: duration_state=duration_check(p)
    except (ValueError,KeyError,FileNotFoundError) as e: duration_state={'state':'blocked','reason':str(e)}
    try: production_gate(p); gate_state='ready'
    except (ValueError,KeyError,FileNotFoundError) as e: gate_state=str(e)
    print(json.dumps({'language':p.language(),'production_gate':gate_state,'duration':duration_state,'export':export_state,'draft_export':draft_state,'music':music_state,'scenes':result,'captions':caption_state,'qa':qa_state,'waiting':p.data.get('waiting',[]),'next':p.data.get('next_action'),'note':'Estimates only; use measured duration after TTS'},ensure_ascii=False,indent=2))

def init(path, preset='generic', duration=None, language=DEFAULT_LANGUAGE, voice_id=None,
         scene_template=None, style=None, theme=None):
    path=Path(path); need(not (path/'project.json').exists(),'Project already exists'); language=normalize_language(language)
    need(scene_template is None or preset=='xyzchem', '--scene-template currently requires --preset xyzchem')
    need(scene_template is None or scene_template in VIDEO_TEMPLATES, 'Unknown video scene template: '+str(scene_template))
    need((style is None and theme is None) or preset=='xyzchem',
         '--style and --theme currently require --preset xyzchem')
    scene_template=scene_template or ('opening' if preset=='xyzchem' else None)
    style,theme=validate_visual_system(style,theme)
    path.mkdir(parents=True,exist_ok=True); (path/'sources').mkdir(exist_ok=True)
    english=is_english(language)
    title='New video' if english else '新视频'; waiting=['Waiting for source material'] if english else ['待提供原始材料']; next_action='Analyze source material and develop narration and storyboard' if english else '分析材料，联合编写旁白与分镜'; narration='Narration to be written.' if english else '待编写旁白。'
    if scene_template:
        profile={'width':VIDEO_PROFILE[0],'height':VIDEO_PROFILE[1],'fps':30,'caption_px':48}
        scene=new_scene_data('s01',scene_template,style,theme,language)
        create_scene_files(path,'s01',scene_template,style,theme,language)
    else:
        (path/'scenes').mkdir(parents=True,exist_ok=True); shutil.copyfile(ROOT/'assets/scene.html',path/'scenes/s01.html')
        if english:
            scene_html=(path/'scenes/s01.html').read_text(encoding='utf-8')
            for old,new in {'lang="zh-CN"':'lang="'+language+'"','视频场景':'Video scene','先理解材料<br>再组织画面':'Study the source<br>then shape the scene','用画面呈现证据，<br>用讲解连接它们。':'Show the evidence<br>and connect it with narration.','为当前材料重新设计此区域':'Redesign this area for the current source.'}.items(): scene_html=scene_html.replace(old,new)
            (path/'scenes/s01.html').write_text(scene_html,encoding='utf-8')
        profile={'width':1920,'height':1080,'fps':30,'caption_px':48}
        scene={'id':'s01','html':'scenes/s01.html','intent':'','visual_notes':'','narration':narration,'caption_phrases':[narration],'claim_ids':[],'assets':[],'dependencies':[],'beats':[],'tail_seconds':.25}
    write(path/'project.json',{'version':1,'language':language,'title':title,'profile':profile,'voice':{'voice_id':voice_id or default_voice_id(language),'speed':1,'vol':1,'pitch':0,'text_normalization':True},'sources':[],'claims':[],'assets':[],'protected_terms':[],'waiting':waiting,'next_action':next_action,'scenes':[scene]})
    data=read(path/'project.json'); data['contract_version']=2
    if preset=='xyzchem':
        data['visual_system']={'style':style,'theme':theme}
        data['brand_component']={'en':'xyzchem-fixed-outro-en-v1','fr-FR':'xyzchem-fixed-outro-fr-v1'}.get(language, 'xyzchem-fixed-outro-v2')
    if duration is not None: data['duration']=duration
    write(path/'project.json',data)
    print(path.resolve())

def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('command',choices=['init','status','approve-script','tts','attach','recover','voices','preview','approve-audio','captions','qa-import','render','approve-music','music-candidates','music-select','music-audition'])
    parser.add_argument('project'); parser.add_argument('--scenes',default='all'); parser.add_argument('--evidence',default='')
    parser.add_argument('--send',action='store_true'); parser.add_argument('--mode',choices=['final','audition'],default=None)
    parser.add_argument('--prompt-key',action='store_true',help='Read the API key without terminal echo; never persist it')
    parser.add_argument('--unit',choices=['ms','s'],default=None); parser.add_argument('--attempt')
    parser.add_argument('--review-hash'); parser.add_argument('--captions',action='store_true'); parser.add_argument('--report'); parser.add_argument('--draft',action='store_true')
    parser.add_argument('--preset',choices=['generic','xyzchem'],default='generic')
    parser.add_argument('--language', choices=sorted(SUPPORTED_LANGUAGES))
    parser.add_argument('--voice-id')
    parser.add_argument('--scene-template',choices=sorted(VIDEO_TEMPLATES))
    parser.add_argument('--style',choices=sorted(VIDEO_MODES))
    parser.add_argument('--theme',choices=sorted(theme for values in VIDEO_MODES.values() for theme in values))
    parser.add_argument('--duration-mode',choices=['approx','max'])
    parser.add_argument('--seconds',type=float)
    parser.add_argument('--candidate-id')
    parser.add_argument('--random',dest='random_select',action='store_true')
    parser.add_argument('--output')
    args=parser.parse_args()
    try:
        if args.command!='init':
            need(args.language is None and args.voice_id is None, '--language and --voice-id are only valid with init')
        if args.command=='init':
            need(bool(args.duration_mode)==(args.seconds is not None), 'Use --duration-mode and --seconds together')
            duration={'mode':args.duration_mode,'seconds':args.seconds} if args.duration_mode else None
            if duration:
                from production_contract import positive
                positive(args.seconds,'duration.seconds')
            init(args.project,args.preset,duration,args.language or DEFAULT_LANGUAGE,args.voice_id,
                 args.scene_template,args.style,args.theme); return
        p=Project(args.project)
        funcs={'status':lambda:status(p),'approve-script':lambda:selected_approval(p,args),'tts':lambda:tts(p,args),'attach':lambda:attach(p,args),'recover':lambda:recover(p,args),'voices':lambda:voices(p,args),'preview':lambda:preview(p,args),'approve-audio':lambda:approve_audio(p,args),'captions':lambda:captions(p),'qa-import':lambda:qa_import(p,args),'render':lambda:render(p,args),'approve-music':lambda:__import__('music_pipeline').approve(p,args),'music-candidates':lambda:music_candidates(p),'music-select':lambda:music_select(p,args),'music-audition':lambda:music_audition(p,args)}
        funcs[args.command]()
    except (ValueError,FileNotFoundError,KeyError) as e:
        print('BLOCKED: '+str(e),file=sys.stderr); sys.exit(2)

if __name__=='__main__': main()

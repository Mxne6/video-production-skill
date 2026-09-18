"""Project-independent pre-voice QA and silent review. Never writes approvals."""
from __future__ import annotations
import argparse
import math
import re
import subprocess
import tempfile
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright
from studio import Project, browser_start, caption_css, ffmpeg, need, sha, stamp, write


def parse_ratio(value):
    """Parse a common aspect-ratio string into a positive width/height float."""
    if isinstance(value, (int, float)):
        return float(value) if value > 0 else None
    text = str(value or '').strip().lower().replace('：', ':').replace('×', 'x')
    match = re.fullmatch(r'(\d+(?:\.\d+)?)\s*(?::|/|x)\s*(\d+(?:\.\d+)?)', text)
    if not match:
        try:
            return float(text) if float(text) > 0 else None
        except ValueError:
            return None
    width, height = (float(part) for part in match.groups())
    return width / height if width > 0 and height > 0 else None


def cover_crop_mismatch(state, tolerance=0.015):
    """Return a detail string when cover will crop a non-matching source image."""
    if state.get('objectFit') != 'cover':
        return None
    natural_width = float(state.get('naturalWidth') or 0)
    natural_height = float(state.get('naturalHeight') or 0)
    frame_width = float(state.get('width') or 0)
    frame_height = float(state.get('height') or 0)
    if min(natural_width, natural_height, frame_width, frame_height) <= 0:
        return None
    source_ratio = natural_width / natural_height
    frame_ratio = frame_width / frame_height
    if abs(source_ratio / frame_ratio - 1) <= tolerance:
        return None
    return (f'source {natural_width:.0f}x{natural_height:.0f} ({source_ratio:.3f}) '
            f'vs frame {frame_width:.0f}x{frame_height:.0f} ({frame_ratio:.3f})')


def validate_plan(p):
    assets = p.data.get('assets', [])
    need(len({a['id'] for a in assets}) == len(assets), 'Duplicate asset IDs')
    by_id = {a['id']: a for a in assets}
    for s in p.scenes():
        plan = s.get('visual_plan', {})
        need(plan.get('medium') in ('typography', 'diagram', 'image', 'mixed') and
             bool(str(plan.get('reason', '')).strip()), s['id'] + ': missing visual_plan')
        duration = s.get('estimated_duration')
        need(isinstance(duration, (float, int)) and math.isfinite(duration) and duration > 0,
             s['id'] + ': estimated_duration must be positive')
        if plan['medium'] in ('image', 'mixed'):
            need(bool(s.get('assets')), s['id'] + ': image plan needs asset IDs')
        p.visual_key(s)
        for aid in s.get('assets', []):
            a = by_id[aid]
            need(a.get('purpose') and a.get('source') and a.get('ratio') and a.get('composition')
                 and a.get('factual_constraints'),
                 aid + ': record purpose, source, ratio, composition and factual_constraints')
            path = p.file(a['path'])
            need(a.get('sha256') == sha(path), aid + ': missing/stale asset sha256')
            if str(a.get('source', '')).startswith('generated'):
                review = a.get('semantic_review', {})
                need(review.get('status') == 'pass' and review.get('asset_sha256') == sha(path)
                     and all(review.get(key) for key in ('intended_message', 'source_refs',
                                                        'observed_content', 'misreading_check')),
                     aid + ': missing/stale semantic review of generated image')
            with Image.open(path) as im:
                im.verify()
                actual_ratio = im.width / im.height
                declared_ratio = parse_ratio(a.get('ratio'))
                need(declared_ratio and abs(actual_ratio / declared_ratio - 1) <= 0.01,
                     aid + ': declared ratio does not match image pixel dimensions')
    return by_id


def estimated_beats(scene, duration):
    """Map declared narration prefixes to estimated times for pre-voice seek QA."""
    narration = scene['narration']
    result = []
    for item in scene.get('beats', []):
        prefix = item.get('after')
        need(isinstance(prefix, str) and prefix and narration.startswith(prefix),
             scene['id'] + ': beat after must be an exact narration prefix')
        result.append({'id': item['id'], 'at': round(duration*len(prefix)/len(narration), 6)})
    return result


IMAGE_STATE = """() => [...document.querySelectorAll('img[data-asset-id]')].map(el => {
  const r=el.getBoundingClientRect(); let visible=r.width>0&&r.height>0;
  for(let p=el;p;p=p.parentElement){const s=getComputedStyle(p);
    if(s.display==='none'||s.visibility==='hidden'||Number(s.opacity)<.05)visible=false;}
  const exposed=[.2,.5,.8].some(x=>[.2,.5,.8].some(y=>
    document.elementFromPoint(r.left+r.width*x,r.top+r.height*y)===el));
  visible=visible&&exposed;
  const styles=getComputedStyle(el);
  return {id:el.dataset.assetId,src:el.currentSrc,visible,
    inside:r.left>=0&&r.top>=0&&r.right<=innerWidth&&r.bottom<=innerHeight,
    width:r.width,height:r.height,naturalWidth:el.naturalWidth,naturalHeight:el.naturalHeight,
    objectFit:styles.objectFit};
})"""

CAPTION_SETUP = """()=>{
  const el=document.createElement('div');
  el.id='vp-caption';
  el.innerHTML='<span></span>';
  document.body.append(el);
  el.querySelector('span').style.visibility='hidden';
}"""

CAPTION_PROBE = """()=>{
  const e=document.querySelector('#vp-caption span');
  const safe=document.querySelector('#vp-caption');
  const r=e.getBoundingClientRect();
  const sr=safe.getBoundingClientRect();
  const lineHeight=parseFloat(getComputedStyle(e).lineHeight);
  const overlaps=[...document.querySelectorAll('[data-safe-check]')]
    .filter(x=>{
      const q=x.getBoundingClientRect();
      return q.bottom>sr.top&&q.top<sr.bottom&&q.left<sr.right&&q.right>sr.left;
    })
    .map(x=>({text:x.textContent.trim().replace(/\\s+/g,' ').slice(0,160),
      top:x.getBoundingClientRect().top,bottom:x.getBoundingClientRect().bottom}));
  return {
    width:e.scrollWidth,
    available:safe.clientWidth,
    caption:{top:r.top,bottom:r.bottom,left:r.left,right:r.right,height:r.height},
    safe:{top:sr.top,bottom:sr.bottom,left:sr.left,right:sr.right},
    overflow:e.scrollWidth>safe.clientWidth||r.top<0||r.bottom>innerHeight||r.height>lineHeight*1.5,
    overlaps
  };
}"""


def review(project, fps=12, render=False, selected='all'):
    p = Project(project)
    need(1 <= fps <= 60, 'Preview fps must be 1–60')
    assets = validate_plan(p)
    scenes = p.scenes(selected)
    w, h = p.data['profile']['width'], p.data['profile']['height']
    out = p.file('review/visual-' + stamp())
    out.mkdir(parents=True)
    report = {'scope': 'pre-voice; estimated timings; no audio or approvals',
              'project_sha256': sha(p.file('project.json')), 'width': w, 'height': h,
              'fps': fps, 'scenes': [], 'issues': []}
    proc = None
    movie = out / 'preview.mp4'
    with tempfile.TemporaryFile() as stderr, sync_playwright() as pw:
        if render:
            proc = subprocess.Popen([ffmpeg(), '-v', 'error', '-y', '-f', 'image2pipe',
                '-vcodec', 'png', '-framerate', str(fps), '-i', 'pipe:0', '-an',
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '20', '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart', str(movie)], stdin=subprocess.PIPE, stderr=stderr)
        browser = browser_start(pw)
        try:
            for s in scenes:
                page = browser.new_page(viewport={'width': w, 'height': h}, device_scale_factor=1)
                errors = []
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.route(re.compile(r'^https?://'), lambda r: r.abort())
                page.goto(p.file(s['html']).as_uri(), wait_until='load')
                page.evaluate('document.fonts.ready')
                page.evaluate('async()=>await Promise.all([...document.images].map(x=>x.decode()))')
                page.add_style_tag(content='*{animation:none!important;transition:none!important}html,body{margin:0!important;padding:0!important;overflow:hidden!important}')
                page.add_style_tag(content=caption_css(p.data['profile']))
                page.evaluate(CAPTION_SETUP)
                duration = float(s['estimated_duration'])
                beats = estimated_beats(s, duration)
                def seek(t, caption='', beat_values=None):
                    page.evaluate('''async o=>{
                        window.productionBeats=o.beats||[];
                        await window.renderAt(o.t,o.d);
                        const e=document.querySelector('#vp-caption span');
                        e.textContent=o.caption;
                        e.style.visibility=o.caption?'visible':'hidden';
                    }''', {'t': t, 'd': duration, 'caption': caption, 'beats': beat_values or []})
                samples = sorted(set([0, min(.8, duration/2), duration/2, max(0, duration-1/fps)]))
                snapshots = []
                for i, t in enumerate(samples):
                    seek(t, beat_values=beats)
                    states = page.evaluate(IMAGE_STATE)
                    snapshots.append({'t': t, 'images': states})
                    page.screenshot(path=str(out / f'{s["id"]}-{i}.png'))
                for aid in s.get('assets', []):
                    states = [x for row in snapshots for x in row['images'] if x['id'] == aid]
                    if not any(x['visible'] and x['inside'] for x in states):
                        report['issues'].append(s['id'] + ': image never visible inside frame: ' + aid)
                    expected = p.file(assets[aid]['path']).as_uri()
                    if not states or any(x['src'] != expected for x in states):
                        report['issues'].append(s['id'] + ': image source differs from asset: ' + aid)
                    seen_fit = set()
                    for state in states:
                        detail = cover_crop_mismatch(state)
                        if detail and detail not in seen_fit:
                            seen_fit.add(detail)
                            report['issues'].append(
                                s['id'] + ': image aspect mismatch under object-fit: cover: '
                                + aid + '; ' + detail
                                + '; generate for the final display ratio or redesign the frame')
                phrases = s.get('caption_phrases', [])
                need(phrases and ''.join(phrases) == s['narration'],
                     s['id'] + ': caption_phrases must reconstruct narration')
                caption_checks = []
                for t in samples:
                    for phrase in phrases:
                        seek(t, phrase, beats)
                        info = page.evaluate(CAPTION_PROBE)
                        check = {'t': t, 'text': phrase, **info}
                        caption_checks.append(check)
                        if info['overflow'] or info['overlaps']:
                            report['issues'].append(
                                s['id'] + ': caption collision or overflow at '
                                + f'{t:.3f}s: {phrase}')
                seek(duration/2, beat_values=beats)
                first = page.screenshot()
                seek(0, beat_values=beats); seek(duration, beat_values=beats); seek(duration/2, beat_values=beats)
                deterministic = first == page.screenshot()
                if not deterministic:
                    report['issues'].append(s['id'] + ': reverse seek is not deterministic')
                frame_count = math.ceil(duration * fps)
                report['scenes'].append({'id': s['id'], 'visual_key': p.visual_key(s),
                    'estimated_duration': duration, 'frames': frame_count,
                    'estimated_beats': beats, 'deterministic': deterministic, 'samples': snapshots,
                    'caption_checks': caption_checks})
                if render:
                    label = '配音前画面预览 · 估计时长'
                    if p.data.get('test_mode'): label = '测试 / ' + label
                    page.evaluate('text=>{const el=document.createElement("div");el.textContent=text;'
                        'el.style.cssText="position:fixed;z-index:2147483647;bottom:2%;right:4%;'
                        'padding:.4em;background:#fafaf8;color:#555;font:600 clamp(12px,1.5vw,24px) sans-serif";'
                        'document.body.appendChild(el)}', label)
                    for frame in range(frame_count):
                        seek(frame/fps, beat_values=beats)
                        proc.stdin.write(page.screenshot(type='png'))
                report['issues'].extend(s['id'] + ': ' + e for e in errors)
                page.close()
                print('Checked ' + s['id'], flush=True)
            if proc:
                proc.stdin.close()
                code = proc.wait()
                stderr.seek(0)
                need(code == 0, stderr.read().decode('utf-8', errors='replace')[-3000:])
                # Decode the entire output; successful encoding alone is insufficient.
                decoded = subprocess.run([ffmpeg(), '-v', 'error', '-xerror', '-i', str(movie),
                    '-progress', 'pipe:1', '-f', 'null', '-'], capture_output=True)
                need(decoded.returncode == 0, decoded.stderr.decode('utf-8', errors='replace'))
                frames = int(re.findall(rb'frame=(\d+)', decoded.stdout)[-1])
                need(frames == sum(x['frames'] for x in report['scenes']), 'Decoded frame count differs')
                report['movie'] = {'path': movie.name, 'sha256': sha(movie),
                    'frames': frames, 'audio': False,
                    'duration': sum(x['frames'] for x in report['scenes'])/fps, 'full_decode': True}
        except Exception as e:
            report['issues'].append(str(e))
            raise
        finally:
            if proc and proc.poll() is None:
                proc.kill(); proc.wait()
            browser.close()
            write(out/'report.json', report)
    need(not report['issues'], 'Visual review failed: ' + str(out/'report.json'))
    print(str(out), flush=True)
    return report, out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    parser.add_argument('--fps', type=int, default=12)
    parser.add_argument('--render', action='store_true')
    parser.add_argument('--scenes', default='all')
    args = parser.parse_args()
    review(args.project, args.fps, args.render, args.scenes)

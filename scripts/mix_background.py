"""Create a separate music review export; never modify approved narration or video."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from studio import ffmpeg, run, read, write, sha

RATE = 48000


def decode(path, seconds=None, filters=None):
    args = [ffmpeg(), '-v', 'error', '-i', path]
    if seconds is not None:
        args += ['-t', str(seconds)]
    if filters:
        args += ['-af', filters]
    result = run(args + ['-f', 'f32le', '-ar', str(RATE), '-ac', '2', 'pipe:1'])
    return np.frombuffer(result.stdout, dtype='<f4').reshape(-1, 2).copy()


def rms(x):
    return float(np.sqrt(np.mean(np.square(x, dtype=np.float64))))


def mix(voice, music, gap_db=24, offset_db=0):
    if len(music) < len(voice):
        raise ValueError('Music is shorter than narration; select a longer track.')
    music = music[:len(voice)].copy()
    block = 480
    levels = np.array([rms(voice[i:i + block]) for i in range(0, len(voice), block)])
    active = levels > max(float(levels.max()) * .04, .001)
    if not active.any() or rms(music) < 1e-6:
        raise ValueError('Narration or music is silent.')
    mask = np.repeat(active, block)[:len(voice)]
    voice_rms = rms(voice[mask])
    music *= voice_rms / rms(music) * 10 ** (-gap_db / 20)
    # Anticipate speech and hold through short pauses to avoid audible pumping.
    held = np.convolve(active.astype(float), np.ones(91), mode='full')[10:10 + len(active)] > 0
    gain = np.where(held, 1., 10 ** (6 / 20))
    smooth = np.convolve(np.pad(gain, (40, 40), mode='edge'), np.ones(81) / 81, mode='valid')
    envelope = np.interp(np.arange(len(voice)), np.arange(len(smooth)) * block, smooth)
    t = np.arange(len(voice)) / RATE
    envelope *= np.minimum(t / 1.2, 1) * np.minimum((len(voice) / RATE - t) / 1.8, 1)
    music *= envelope[:, None] * 10 ** (offset_db / 20)
    # Preserve voice samples, reducing the music globally if headroom is small.
    peak_voice = float(np.abs(voice).max())
    if peak_voice >= .98:
        raise ValueError('Narration has insufficient headroom; review source levels.')
    headroom_scale = min(1., (.98 - peak_voice) / max(float(np.abs(music).max()), 1e-9))
    music *= headroom_scale
    mixed = voice + music
    return mixed, music, {
        'voice_gain_db': 0, 'target_gap_db': gap_db,
        'music_offset_db': offset_db,
        'measured_active_voice_music_gap_db': 20 * np.log10(voice_rms / rms(music[mask])),
        'music_headroom_scale': headroom_scale, 'peak': float(np.abs(mixed).max()),
        'duration': len(voice) / RATE, 'fade_in_seconds': 1.2, 'fade_out_seconds': 1.8,
        'pause_lift_db': 6, 'auditory_review': 'pending',
    }


def encode_wav(path, data, codec="pcm_s24le"):
    import subprocess
    result = subprocess.run([ffmpeg(), '-v', 'error', '-n', '-f', 'f32le', '-ar', str(RATE),
                             '-ac', '2', '-i', 'pipe:0', '-c:a', codec, str(path)],
                            input=data.astype('<f4').tobytes(), capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace'))


def video_hash(path):
    return hashlib.sha256(run([ffmpeg(), '-v', 'error', '-i', path, '-map', '0:v:0',
                              '-c:v', 'copy', '-f', 'h264', 'pipe:1']).stdout).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    parser.add_argument('--video', required=True)
    parser.add_argument('--music', required=True)
    parser.add_argument('--license', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--gap-db', type=float, default=24)
    parser.add_argument('--offset-db', type=float, default=0)
    args = parser.parse_args()
    if not 6 <= args.gap_db <= 36:
        parser.error('--gap-db must be between 6 and 36')
    if not -18 <= args.offset_db <= 8:
        parser.error('--offset-db must be between -18 and 8')
    p = args.project.resolve()
    video, music, license_path = [p / x for x in (args.video, args.music, args.license)]
    license_data = read(license_path)
    if not all(license_data.get(k) for k in ('title', 'artist', 'source_url', 'license', 'attribution')):
        raise ValueError('License record is incomplete.')
    captions_path = p / read(p / 'state.json')['captions']
    captions = read(captions_path)
    narration = p / captions['bundle']['audio']
    out = p / args.output
    out.mkdir(parents=True, exist_ok=False)
    voice = decode(narration)
    bed = decode(music, len(voice) / RATE, 'highpass=f=110,lowpass=f=7000')
    mixed, bed, report = mix(voice, bed, args.gap_db, args.offset_db)
    encode_wav(out / 'mix.wav', mixed)
    encode_wav(out / 'music-bed.wav', bed)
    target = out / 'review.mp4'
    run([ffmpeg(), '-v', 'error', '-n', '-i', video, '-i', out / 'mix.wav', '-map', '0:v:0',
         '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', target])
    run([ffmpeg(), '-v', 'error', '-i', target, '-f', 'null', '-'])
    report['video_bitstream_unchanged'] = video_hash(video) == video_hash(target)
    decoded = decode(target)
    report['encoded_peak'] = float(np.abs(decoded).max())
    report['encoded_duration'] = len(decoded) / RATE
    if not report['video_bitstream_unchanged'] or report['encoded_peak'] >= 1 or abs(len(decoded) - len(voice)) > RATE * .1:
        raise ValueError('Export validation failed.')
    report['inputs'] = {str(x.relative_to(p)): sha(x) for x in (video, narration, music, license_path, captions_path)}
    report['outputs'] = {x.name: sha(x) for x in (target, out / 'mix.wav', out / 'music-bed.wav')}
    report['license'] = license_data
    report['review_identity'] = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()
    write(out / 'manifest.json', report)
    (out / 'ATTRIBUTION.txt').write_text(license_data['attribution'] + '\nEdited: trimmed, filtered, faded and mixed under narration.\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

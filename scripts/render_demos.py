"""Encode browser screen captures or rebuild previews from the distributed videos."""
import argparse
from bisect import bisect_right
import hashlib
import json
from pathlib import Path
import subprocess

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / 'docs' / 'media'
CLIPS = {'query-replay': 0.8, 'root-transport': 1.0, 'acquisition-cost': 6.7}
FPS = 12


def timecode(seconds):
    milliseconds = round(seconds * 1000)
    hours, remainder = divmod(milliseconds, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f'{hours:02}:{minutes:02}:{seconds:02}.{milliseconds:03}'


def encode_capture(directory, name):
    take = json.loads((directory / 'take.json').read_text())
    frames = take['frames']
    times = [f['t'] for f in frames]
    video = MEDIA / (name + '.mp4')
    cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
           '-s', '1280x720', '-r', str(FPS), '-i', '-', '-an', '-c:v', 'libx264',
           '-threads', '2', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p',
           '-movflags', '+faststart', '-metadata', 'artist=Zijia Wang', str(video)]
    previous = -1
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for tick in range(round(take['duration'] * FPS)):
            index = max(0, bisect_right(times, tick / FPS) - 1)
            if index != previous:
                with Image.open(directory / frames[index]['file']) as source:
                    # Crop only the margins and the paper backlink above the instrument.
                    data = source.convert('RGB').crop((40, 55, 1320, 775)).tobytes()
                previous = index
            process.stdin.write(data)
    finally:
        process.stdin.close()
        return_code = process.wait()
    if return_code:
        raise RuntimeError(f'Encoding failed for {name}')
    cues = []
    for cue in take['cues']:
        if not cues or cue['caption'] != cues[-1]['caption']:
            cues.append(cue)
    lines = ['WEBVTT', '']
    for i, cue in enumerate(cues):
        end = cues[i + 1]['t'] if i + 1 < len(cues) else take['duration']
        lines.extend([f"{timecode(cue['t'])} --> {timecode(end)}", cue['caption'], ''])
    video.with_suffix('.vtt').write_text('\n'.join(lines), encoding='utf-8')


def previews(name, poster_time):
    video = MEDIA / (name + '.mp4')
    prefix = ['ffmpeg', '-v', 'error', '-y', '-threads', '2']
    subprocess.run(prefix + ['-ss', str(poster_time), '-i', str(video),
                   '-frames:v', '1', str(MEDIA / (name + '-poster.png'))], check=True)
    filters = ('fps=5,scale=840:-1:flags=lanczos,split[a][b];'
               '[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer')
    subprocess.run(prefix + ['-i', str(video), '-filter_complex_threads', '1',
                   '-filter_complex', filters, '-loop', '0', str(video.with_suffix('.gif'))], check=True)
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries',
                       'stream=codec_name,width,height,pix_fmt:format=duration', '-of', 'json', str(video)]))
    assets = [video, video.with_suffix('.gif'), video.with_suffix('.vtt'), MEDIA / (name + '-poster.png')]
    return {'name': name, 'duration_seconds': float(probe['format']['duration']), 'encoding': probe,
            'files': {p.name: {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                      for p in assets}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--captures', type=Path, help='Optional directory of timestamped browser captures.')
    args = parser.parse_args()
    demos = []
    for name, poster_time in CLIPS.items():
        if args.captures:
            encode_capture(args.captures / name, name)
        demos.append(previews(name, poster_time))
    manifest = {'author': 'Zijia Wang', 'source': 'Browser screen recordings of docs/explorer/',
                'description': 'Playback includes time spent operating the controls.',
                'demos': demos}
    (MEDIA / 'media-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()

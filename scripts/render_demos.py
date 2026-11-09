"""Encode actual browser captures with readable captions, or rebuild previews."""
import argparse
from bisect import bisect_right
import hashlib
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageFont

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


def caption_font(size):
    for path in ('/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
                 '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                 'Arial.ttf', 'DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def wrap_caption(caption, draw, font, max_width):
    lines, current = [], ''
    for word in caption.split():
        candidate = (current + ' ' + word).strip()
        if current and draw.textlength(candidate, font=font) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def encode_capture(directory, name):
    take = json.loads((directory / 'take.json').read_text())
    frames = take['frames']
    duration = float(take['duration'])
    if not frames or duration <= 0:
        raise ValueError(f'{name}: a positive duration and at least one frame are required')
    times = [float(f['t']) for f in frames]
    if times != sorted(times) or times[0] < 0 or times[-1] >= duration:
        raise ValueError(f'{name}: frame timestamps must be ordered within the duration')
    cues = []
    for cue in take.get('cues', []):
        if not cues or cue['caption'] != cues[-1]['caption']:
            cues.append(cue)
    cue_times = [float(c['t']) for c in cues]
    if cue_times != sorted(cue_times) or any(t < 0 or t >= duration for t in cue_times):
        raise ValueError(f'{name}: caption timestamps must be ordered within the duration')

    # Keep every screenshot pixel. A one-pixel edge pad makes H.264 dimensions even.
    sizes = []
    for frame in frames:
        with Image.open(directory / frame['file']) as source:
            sizes.append(source.size)
    width = max(size[0] for size in sizes)
    source_height = max(size[1] for size in sizes)
    width += width % 2
    font_size = min(26, max(18, round(width / 55)))
    font = caption_font(font_size)
    band_height = font_size * 3 + 26
    height = source_height + band_height
    height += height % 2
    video = MEDIA / (name + '.mp4')
    cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
           '-s', f'{width}x{height}', '-r', str(FPS), '-i', '-', '-an',
           '-c:v', 'libx264', '-threads', '2', '-preset', 'medium', '-crf', '17',
           '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
           '-metadata', 'artist=Zijia Wang', str(video)]
    previous, data = None, None
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for tick in range(round(duration * FPS)):
            elapsed = tick / FPS
            index = max(0, bisect_right(times, elapsed) - 1)
            cue_index = bisect_right(cue_times, elapsed) - 1
            key = (index, cue_index)
            if key != previous:
                canvas = Image.new('RGB', (width, height), 'white')
                with Image.open(directory / frames[index]['file']) as source:
                    image = source.convert('RGB')
                    canvas.paste(image, ((width - image.width) // 2, 0))
                draw = ImageDraw.Draw(canvas)
                cursor = frames[index].get('cursor')
                if cursor is not None:
                    # Coordinates come from the actual interacted element in the capture.
                    cx, cy = float(cursor['x']), float(cursor['y'])
                    if not (0 <= cx < image.width and 0 <= cy < image.height):
                        raise ValueError(f'{name}: cursor must lie within its source capture')
                    cx += (width - image.width) // 2
                    if cursor.get('click'):
                        draw.ellipse((cx - 14, cy - 14, cx + 14, cy + 14),
                                     outline='#6691ac', width=2)
                    shape = [(cx, cy), (cx, cy + 25), (cx + 6, cy + 19),
                             (cx + 12, cy + 31), (cx + 17, cy + 28),
                             (cx + 11, cy + 17), (cx + 22, cy + 17)]
                    draw.polygon(shape, fill='white', outline='#253640', width=2)
                draw.rectangle((0, source_height, width, height), fill='#eef3f6')
                draw.line((0, source_height, width, source_height), fill='#cfdae1', width=1)
                if cue_index >= 0:
                    caption = cues[cue_index]['caption']
                    lines = wrap_caption(caption, draw, font, width - 70)
                    if len(lines) > 2:
                        raise ValueError(f'{name}: shorten caption to two lines: {caption}')
                    line_height = font_size + 7
                    y = source_height + (height - source_height - len(lines) * line_height) // 2
                    for line in lines:
                        x = (width - draw.textlength(line, font=font)) / 2
                        draw.text((x, y), line, font=font, fill='#293d49')
                        y += line_height
                data = canvas.tobytes()
                previous = key
            process.stdin.write(data)
    finally:
        process.stdin.close()
        return_code = process.wait()
    if return_code:
        raise RuntimeError(f'Encoding failed for {name}')

    lines = ['WEBVTT', '']
    for i, cue in enumerate(cues):
        end = cues[i + 1]['t'] if i + 1 < len(cues) else duration
        lines.extend([f"{timecode(cue['t'])} --> {timecode(end)}", cue['caption'], ''])
    video.with_suffix('.vtt').write_text('\n'.join(lines), encoding='utf-8')
    return min(float(take.get('poster_time', CLIPS[name])), max(0, duration - 1 / FPS))


def previews(name, poster_time):
    video = MEDIA / (name + '.mp4')
    prefix = ['ffmpeg', '-v', 'error', '-y', '-threads', '2']
    subprocess.run(prefix + ['-ss', str(poster_time), '-i', str(video),
                   '-frames:v', '1', str(MEDIA / (name + '-poster.png'))], check=True)
    poster = MEDIA / (name + '-poster.png')
    with Image.open(poster) as source:
        source.convert('RGB').quantize(colors=256).save(poster, optimize=True)
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
            poster_time = encode_capture(args.captures / name, name)
        demos.append(previews(name, poster_time))
    manifest = {'author': 'Zijia Wang', 'source': 'Actual browser captures of docs/explorer/',
                'description': 'Edited screen captures of real UI interactions, with caption and recorded click-target cursor overlays. Playback duration is not execution time.',
                'demos': demos}
    (MEDIA / 'media-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()

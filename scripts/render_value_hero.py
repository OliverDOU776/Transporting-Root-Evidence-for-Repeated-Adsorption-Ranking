"""Render the opening animation (scripts/value_hero_story.html, a CSS-animated SVG) to docs/media/value-hero.*

The page is opened in headless Chromium. Before each screenshot every CSS animation is paused and moved to the same
time stamp, so the export is deterministic and frame-accurate. Molecular drawings, crystals and the gallery are
schematic; the transported bracket and score bound are exact arithmetic of the analytic example, and the two times
are the measured CRAFTED workload recorded in docs/media/value-hero-data.json. Animation pacing is not execution time.

    python -m pip install playwright && python -m playwright install chromium     # FFmpeg with libx264 is also needed
    python scripts/render_value_hero.py
"""
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / 'docs' / 'media'
W, H, DURATION = 1280, 660, 20.0
SEEK = '(t) => { for (const a of document.getAnimations()) { a.pause(); a.currentTime = t; } }'
SCENES = [(0.0, 'One library of porous adsorbents'), (4.0, 'A new condition repeats every equilibrium solve'),
          (8.0, 'Transport the earlier root; arithmetic bounds the new score'), (13.0, 'Rule out first, solve the rest, same ranking'),
          (16.5, 'Measured repeated-query payoff')]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--source', type=Path, default=ROOT / 'scripts' / 'value_hero_story.html')
    ap.add_argument('--fps', type=int, default=15)
    ap.add_argument('--poster', type=float, default=19.0, help='time (s) of the poster frame')
    ap.add_argument('--stills', type=Path, help='also save one still per second into this directory (for checking)')
    a = ap.parse_args()
    n = round(DURATION * a.fps)
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as p:
        browser = p.chromium.launch(); page = browser.new_page(viewport={'width': W, 'height': H}, device_scale_factor=1)
        page.goto(a.source.resolve().as_uri()); page.wait_for_timeout(300)
        for i in range(n):
            page.evaluate(SEEK, 1000.0 * i / a.fps); page.screenshot(path=f'{tmp}/{i:04d}.png')
        page.evaluate(SEEK, 1000.0 * a.poster); page.screenshot(path=str(MEDIA / 'value-hero-poster.png'))
        if a.stills:
            a.stills.mkdir(parents=True, exist_ok=True)
            for s in range(int(DURATION)):
                page.evaluate(SEEK, 1000.0 * (s + 0.75)); page.screenshot(path=str(a.stills / f'{s:02d}.png'))
        browser.close()
        ff = ['ffmpeg', '-y', '-v', 'error', '-framerate', str(a.fps), '-i', f'{tmp}/%04d.png']
        subprocess.run(ff + ['-an', '-c:v', 'libx264', '-threads', '2', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                             '-metadata', 'artist=Zijia Wang, Haoliang Hong, Xuhui Li, Jingyang Bai, Binjian Nie', str(MEDIA / 'value-hero.mp4')], check=True)
        flt = 'fps=8,scale=760:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96:stats_mode=diff[p];[b][p]paletteuse=dither=none:diff_mode=rectangle'   # dark gradients: no dither keeps the GIF small
        subprocess.run(ff + ['-filter_complex', flt, '-loop', '0', str(MEDIA / 'value-hero.gif')], check=True)
    data_path = MEDIA / 'value-hero-data.json'
    story = json.loads(data_path.read_text())          # analytic example and measured workload are kept as recorded
    story.update(title='Same ranked answer. Less repeated work.', duration_seconds=int(DURATION), size=[W, H], fps=a.fps,
                 source='scripts/value_hero_story.html (CSS-animated SVG, drawn by Gemini 4 Argon from a written brief), rendered by scripts/render_value_hero.py',
                 scope='Molecules, crystals, the candidate gallery, gauges and the shortlist are schematic. The transported bracket [4/15, 11/30] and the score bound 11/19 (shown as 0.58) are exact arithmetic of the analytic example, not an experimental CO2/N2 isotherm. The two times are a separate measured workload. Animation pacing is not execution time.',
                 scenes=[{'start': t, 'title': s} for t, s in SCENES], files={})
    for name in ('value-hero.mp4', 'value-hero.gif', 'value-hero-poster.png'):
        f = MEDIA / name; story['files'][name] = {'bytes': f.stat().st_size, 'sha256': hashlib.sha256(f.read_bytes()).hexdigest()}
        print(name, f.stat().st_size // 1024, 'KB')
    data_path.write_text(json.dumps(story, indent=2) + '\n')


if __name__ == '__main__':
    main()

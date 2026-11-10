# Adsorption workbench recordings

These MP4s show actual interactions with the [public adsorption explorer](https://oliverdou776.github.io/Transporting-Root-Evidence-for-Repeated-Adsorption-Ranking/explorer/). Each clip includes an animated GIF, a poster, visible captions, click-target cursor overlays and an English WebVTT track. Screen captures are held and edited for readability; playback duration is not benchmark execution time.

| Recording | User workflow | Practical value and source |
|---|---|---|
| [Rank, inspect and export](query-replay.mp4) | Enter pressure and gas-1 feed fraction, run a ranking query, inspect a selected pair's isotherms, change the operating condition and export the computed shortlist as CSV. | Obtain candidate IDs, selectivities and query conditions for subsequent analysis. The browser performs complete binary IAST solves over 144 synthetic curve pairs. It does not run the native transport executor. |
| [Inspect evidence reuse](root-transport.mp4) | Change destination pressure, observe the transition from exclusion to refinement, then adjust the eligible score cutoff. | See when an earlier root enclosure permits an exclusion without a fresh integral evaluation, and when the numerical solver must do more work. This is the exact analytic Henry example with source root 1/3. |
| [Compare measured cost](acquisition-cost.mp4) | Compare a one-query CRAFTED run with 64 queries, then inspect the adverse NIST distant-state/top-50 workload. | Assess whether repeated queries repay preparation and acquisition cost. Values come from the original paired Transport/LeanCap measurements in the [published result table](../../evidence/published_results.csv), including losses. |

The Python/C++ package implements the executor evaluated in the paper. The browser's synthetic ranking view uses double-precision complete solves; its molecular illustrations indicate the application area and are not simulated CO₂/N₂ measurements. The six native reference states in `query-replay-data.json` provide top-5 ID and score checks. The cost view uses separate paper measurements and does not benchmark the synthetic browser pool.

## Repeat the workflow

From the repository root, serve the page with `python -m http.server 8000 --directory docs` and open `http://localhost:8000/explorer/`. Operate the controls listed above. The CSV export saves the last **computed** query, so editing a form field without running it does not change the exported conditions.

The synthetic reference data can be rebuilt with `python scripts/record_demo.py`. The explorer's timing data are the CSV rows with `study=original` and `control=LeanCap`, serialized to JSON.

To regenerate posters, GIFs and the media manifest from the supplied MP4s, install FFmpeg with ffprobe and libx264, then run:

```sh
python -m pip install -e '.[demo]'
python scripts/render_demos.py
```

For new screen captures, run `python scripts/render_demos.py --captures DIRECTORY`. Give each clip a subdirectory named `query-replay`, `root-transport` or `acquisition-cost`. Each contains the actual image frames and a `take.json`:

```json
{
  "duration": 12,
  "poster_time": 4,
  "frames": [{"t": 0, "file": "000.png"}, {"t": 4, "file": "001.png"}],
  "cues": [{"t": 0, "caption": "Set the operating condition."}, {"t": 4, "caption": "Run the query and inspect the shortlist."}]
}
```

Timestamps are seconds on the edited playback timeline. `poster_time` is optional. The encoder infers image dimensions, preserves the full captured UI and adds a separate caption band below it. It pads odd edges by one pixel for H.264 compatibility. A frame may optionally include `"cursor": {"x": 200, "y": 300, "click": true}` using coordinates recorded from the actual interaction target relative to that capture. The encoder draws a small pointer and, for a click, a subtle ring; it does not synthesize interface elements. Captions should fit at most two lines. Outputs are H.264 MP4, 840-pixel-wide GIF, PNG poster, WebVTT captions and a SHA-256 media manifest.

## Opening animation

`value-hero.mp4` / `value-hero.gif` is the twenty-second looping summary at the top of the project page and the README. It is a CSS-animated SVG (`scripts/value_hero_story.html`, drawn by Gemini 4 Argon from a written brief) rendered frame-accurately in headless Chromium by `python scripts/render_value_hero.py` (Playwright and FFmpeg required). Molecules, the zeolite-like cage, the candidate gallery, gauges and the shortlist are schematic. The transported bracket [4/15, 11/30] and the score bound 0.58 are exact arithmetic of the analytic example; 5.22 s and 2.61 s are the measured CRAFTED workload. Sources and hashes are recorded in `value-hero-data.json`.

# Research demonstrations

These silent demonstrations distinguish native execution, an analytical example,
and published timing summaries. Their presentation pacing is schematic and never
represents elapsed numerical execution time.

| File stem | Duration | Evidence and interpretation |
| --- | ---: | --- |
| `query-replay` | 21 s | Recorded native execution on 144 synthetic PWL curve pairs. A paid complete acquisition is followed by a same-state check and five changed states. Top-5 IDs and scores agree with a cold complete solve. Cumulative spreading-pressure probes include common native setup and Transport's paid acquisition. Probe counts are API calls, not elapsed time or transcendental-operation counts. Bars are scaled within each query. |
| `root-transport` | 16 s | Exact analytical Henry example from the manuscript: equal feed, `q1(p)=p`, `q2(p)=2p`, finite support `[0,10]`, pressure `1 → 1.1`. The source root `1/3` transports to `[4/15,11/30]`; its selectivity upper `11/19` is below an established eligible cut of `1`. This illustrates conditional exclusion, not a new benchmark measurement. |
| `acquisition-cost` | 20 s | Original CRAFTED CO2/N2 top-1 near/far results at measured prefixes 1, 8, 16, 32, 64. Transport/LeanCap ratios are paired within each of three technical blocks. Points show medians, bars observed minimum/maximum; no confidence intervals or interpolated measurements. Setup, paid acquisition and teardown are included. |

Each stem has an H.264 MP4 (1280 × 720, 12 fps, `yuv420p`, fast start,
no audio), an 800 × 450 GIF with held scientific states, a full-resolution
`-poster.png`, and English `.vtt` captions. Videos have no autoplay requirement.

`query-replay-data.json` contains the synthetic corpus, recorded outputs and
source binding. `root-transport-data.json` records the exact fractional
derivation. The timing demonstration reads `../../evidence/published_results.csv`;
it does not rerun a benchmark. `media-manifest.json` records encoding properties,
input hashes and media hashes.

## Regenerate

Use Linux with the repository's native C++17/GCC/libquadmath requirements,
Python, FFmpeg (including `ffprobe` and `libx264`), and DejaVu fonts. On
Debian/Ubuntu, install the additional system tools with:

```bash
sudo apt-get install ffmpeg fonts-dejavu-core
```

From the repository root:

```bash
python -m pip install -e '.[demo]'
python scripts/record_demo.py
python scripts/render_demos.py
```

The renderer uses Pillow and the DejaVu Sans/Serif files in
`/usr/share/fonts/truetype/dejavu`. Rendering does not require a GPU, network
access, a hosted service or an image-generation model. The recorder asserts
agreement with complete solves; the renderer checks the recorded cumulative
probe accounting. Its analytical transport bounds use Python exact fractions.

The media do not imply universal runtime improvement, physical chemistry
validation, or all-input floating-point soundness. The paper and result tables
retain adverse regimes and the stated numerical assumptions.

Author: Zijia Wang.

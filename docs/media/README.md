# Explorer screen recordings

The three MP4 files record browser interactions with the [public adsorption explorer](https://oliverdou776.github.io/Transporting-Root-Evidence-for-Repeated-Adsorption-Ranking/explorer/). Each recording includes a GIF preview, poster and optional English WebVTT captions.

| View | Recorded interaction | Underlying calculation or data |
|---|---|---|
| Query rankings | Change the pressure from 0.3 to 2, change the gas-1 feed from 0.15 to 0.9, run the query and select a ranked pair. | The browser integrates finite piecewise-linear pure-gas isotherms and solves supported binary equilibria by bisection. Clicking a pair displays its two stored curves. The synthetic pool contains 144 pairs. |
| Root bounds | Increase destination pressure at fixed equal feed, observe the change from exclusion to refinement, then raise the eligible score cutoff. | The Henry example uses a source root of 1/3 and an exact analytic transport rule. The plot displays the destination enclosure and the cutoff in adsorbed-fraction coordinates. |
| Measured cost | Inspect the 1-, 8- and 64-query prefixes, then switch from CRAFTED near/top-1 to NIST far/top-50. | The three block values, median and observed range come from the original Transport/LeanCap measurements in the [published result table](../../evidence/published_results.csv). |

The Python/C++ package implements the executor evaluated in the paper. The browser ranker uses double precision and complete solves for the synthetic example. The six native reference states in `query-replay-data.json` provide top-5 ID and score checks. Video duration includes time spent operating the interface.

## Reproduce the views

From the repository root, serve the page with `python -m http.server 8000 --directory docs` and open `http://localhost:8000/explorer/`. Use the controls in the table above to repeat the recordings. The synthetic data can be rebuilt with `python scripts/record_demo.py`. The explorer timing data are the CSV rows with `study=original` and `control=LeanCap`, serialized to JSON.

To regenerate posters, GIFs and the media manifest from the supplied MP4s, install FFmpeg with ffprobe and libx264, then run the following commands.

```sh
python -m pip install -e '.[demo]'
python scripts/render_demos.py
```

For new timestamped screen captures, the encoder accepts `--captures DIRECTORY`. Give each clip its own subdirectory named after its file stem. Each subdirectory contains image frames and a `take.json` with elapsed `duration` in seconds, a `frames` list of timestamp and filename pairs (`t`, `file`), and a `cues` list of timestamp and caption pairs (`t`, `caption`). The provided crop is for the original 1363 × 936 browser viewport. The output is 1280 × 720 H.264 video with the recorded interaction timing.

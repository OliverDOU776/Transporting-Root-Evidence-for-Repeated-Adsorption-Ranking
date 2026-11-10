<div align="center">

# Transporting Root Evidence<br>for Repeated Adsorption Ranking

<p><a href="mailto:zijia.wang@said.oxford.edu">Zijia Wang</a><sup>∗</sup>, <a href="mailto:haoliang.hong@eng.ox.ac.uk">Haoliang Hong</a><sup>∗</sup>, <a href="mailto:lixuhui25@mails.ucas.ac.cn">Xuhui Li</a><sup>†</sup>, <a href="mailto:j.bai22@imperial.ac.uk">Jingyang Bai</a><sup>‡</sup>, <a href="mailto:binjian.nie@eng.ox.ac.uk">Binjian Nie</a><sup>∗</sup></p>

<sup>∗</sup>University of Oxford, United Kingdom · <sup>†</sup>University of Chinese Academy of Sciences, China · <sup>‡</sup>Imperial College London, United Kingdom

<details><summary>Author contact</summary>

Zijia Wang: [zijia.wang@said.oxford.edu](mailto:zijia.wang@said.oxford.edu)

Haoliang Hong: [haoliang.hong@eng.ox.ac.uk](mailto:haoliang.hong@eng.ox.ac.uk)

Xuhui Li: [lixuhui25@mails.ucas.ac.cn](mailto:lixuhui25@mails.ucas.ac.cn)

Jingyang Bai: [j.bai22@imperial.ac.uk](mailto:j.bai22@imperial.ac.uk)

Binjian Nie: [binjian.nie@eng.ox.ac.uk](mailto:binjian.nie@eng.ox.ac.uk)

</details>

[Paper](docs/assets/paper.pdf) · [Project page](https://oliverdou776.github.io/Transporting-Root-Evidence-for-Repeated-Adsorption-Ranking/) · [Interactive demo](https://oliverdou776.github.io/Transporting-Root-Evidence-for-Repeated-Adsorption-Ranking/explorer/) · [Demo video](https://oliverdou776.github.io/Transporting-Root-Evidence-for-Repeated-Adsorption-Ranking/media/query-replay.mp4) · [BibTeX](#citation)

**Reuse numerical evidence when screening adsorption candidates across changing conditions.**

</div>

[![Twenty-second explanation: changing pressure creates another screening query; an earlier solve bounds a candidate below the shortlist cutoff, avoiding its fresh solve while uncertain candidates are still tested; the final measured example shows 2.61 seconds versus 5.22 seconds including setup and acquisition](docs/media/value-hero.gif?v=20261110-1)](https://oliverdou776.github.io/Transporting-Root-Evidence-for-Repeated-Adsorption-Ranking/media/value-hero.mp4?v=20261110-1)

**Same ranked answer. Less repeated numerical work.** The opening animation connects the chemistry screening question to the computation that reuse can skip. Molecular drawings and the screening flow are schematic; the bound is an exact analytic example, and the final timings come from a separate representative measured workload. [Animation data and derivation](docs/media/value-hero-data.json).

Pressure and feed sweeps reuse the same pure-gas curves, yet each mixture score requires a new implicit equilibrium. We transport an earlier **root enclosure** to the next condition. Its score bound can rule out a candidate before another integral evaluation. The molecular drawings provide application context; the method operates on isotherm curves.

In a representative 64-query CRAFTED CO₂/N₂ stream with 16,010 configuration pairs, median paid time was **2.61 s for Transport versus 5.22 s for LeanCap**. The median paired time ratio was **0.500**, including setup, acquisition and teardown. The benefit depends on the workload: all original one-query CRAFTED prefixes lose to LeanCap.

## See how to use it

[![Screen recording of entering conditions, ranking candidate pairs and inspecting isotherms in the adsorption explorer](docs/media/query-replay.gif?v=20261109-3)](https://oliverdou776.github.io/Transporting-Root-Evidence-for-Repeated-Adsorption-Ranking/media/query-replay.mp4)

**Screen candidates, inspect the shortlist, then change the operating condition.** The recording operates the same [public explorer](https://oliverdou776.github.io/Transporting-Root-Evidence-for-Repeated-Adsorption-Ranking/explorer/) that you can open yourself.

1. Enter total pressure, gas-1 feed fraction and the number of results to return.
2. Run the query and select a ranked pair to inspect its two pure-gas isotherms.
3. Change the pressure or feed to compare the shortlist at another condition.
4. Export the computed shortlist as CSV for subsequent analysis.

The ranking view computes a complete binary IAST solve over **144 synthetic curve pairs** in the browser. At six stored states, it compares its first five IDs and scores with native reference outputs. This small example explains the screening workflow; it is separate from the paper's measured transport timings.

| View | What you do | What you learn |
|---|---|---|
| [Query rankings](https://oliverdou776.github.io/Transporting-Root-Evidence-for-Repeated-Adsorption-Ranking/explorer/#ranking) | Enter conditions and inspect ranked pairs | Which synthetic candidates rank highest, and the curves behind each result |
| [Root bounds](https://oliverdou776.github.io/Transporting-Root-Evidence-for-Repeated-Adsorption-Ranking/explorer/#bounds) · [Video](https://oliverdou776.github.io/Transporting-Root-Evidence-for-Repeated-Adsorption-Ranking/media/root-transport.mp4) | Adjust destination pressure and the eligible cutoff | When a transported bound can avoid a fresh numerical evaluation |
| [Measured cost](https://oliverdou776.github.io/Transporting-Root-Evidence-for-Repeated-Adsorption-Ranking/explorer/#cost) · [Video](https://oliverdou776.github.io/Transporting-Root-Evidence-for-Repeated-Adsorption-Ranking/media/acquisition-cost.mp4) | Select relation, stream, top-k and query horizon | When the observed savings repay acquisition, including adverse cases |

The root-bounds view is an analytic illustration. The cost view reads published measurements; it does not run a benchmark in your browser. To use your own curves with the native transport executor, follow [Installation](#installation) and [Usage](#usage).

## Method

A warm start reduces numerical work after a candidate reaches the solver. A transported root bound may eliminate the candidate before a new integral evaluation.

The engine ranks binary mixtures by IAST selectivity. Pure-gas isotherms are positive piecewise-linear curves with a linear origin rule and declared finite upper support. Given a genuine source enclosure and a supported destination equilibrium, two partial-pressure ratios provide an arithmetic destination enclosure. A shared static cap index schedules candidates, and distinct eligible candidates supply lower witnesses for top-k selection. Inconclusive numerical predicates trigger refinement.

![Analytic example of transporting a root enclosure](docs/assets/transported-evidence.svg)

**An exclusion before a fresh solve.** For q₁(p) = p and q₂(p) = 2p, the equal-feed source root is x* = 1/3. After pressure changes from 1 to 1.1, the transported score upper bound is 11/19, below a cutoff of 1. A wider bound from a negative threshold test remains inconclusive. [Operate this example](https://oliverdou776.github.io/Transporting-Root-Evidence-for-Repeated-Adsorption-Ranking/explorer/#bounds).

## Experimental results

Across four 64-query CRAFTED streams, Transport uses **0.456–0.655×** the paid time of LeanCap. A separate matched study measures **0.485–0.623×** on-demand warm solving, with every paired block favorable. All eight original near/far configurations are retained below.

**Paid-time ratios at 64 queries.** Smaller than 1 favors Transport. Each value is a median of three paired within-block ratios. “Faster blocks” refers to the LeanCap comparison; WarmOnDemand uses a separate set of clocks.

| Relation | Stream | k | Transport / LeanCap | Faster blocks | Transport / WarmOnDemand |
|---|---|---:|---:|---:|---:|
| CRAFTED | near | 1 | 0.500 | 3/3 | 0.485 |
| CRAFTED | near | 50 | 0.456 | 3/3 | 0.492 |
| CRAFTED | far | 1 | 0.601 | 3/3 | 0.584 |
| CRAFTED | far | 50 | 0.655 | 3/3 | 0.623 |
| NIST | near | 1 | 0.744 | 3/3 | 0.617 |
| NIST | near | 50 | 0.761 | 3/3 | 0.767 |
| NIST | far | 1 | 0.831 | 3/3 | 0.833 |
| NIST | far | 50 | 1.029 | 1/3 | 0.961 |

Original mechanism cohorts contain 16,010 CRAFTED **configuration pairs** (which can share materials) and 353 NIST curve pairs. WarmOnDemand values come from separately timed continuation cohorts. Three technical blocks provide descriptive medians and observed ranges, not confidence intervals.

The representative CRAFTED near/top-1 arm medians are 2.6127 s for Transport and 5.2196 s for LeanCap. Paid time includes native preparation, acquisition, query processing, output conversion and teardown. Common data loading, immutable pool preparation, native compilation/loading and reference checks are outside the timers.

**Where the benefit ends.** All original one-query CRAFTED prefixes lose to LeanCap. Larger state changes, small pools, high k and unfavorable acquisition states can remove the advantage. Historical solved-root bounds account for the demonstrated savings; additional negative-witness retention does not consistently improve paid time. The original NIST far/k = 50 result is mixed against LeanCap (1/3 favorable blocks).

[All 160 curated prefix comparisons](evidence/published_results.csv) · [Exact values, observed ranges and provenance](evidence/published_results.json) · [Full paper](docs/assets/paper.pdf)

## Installation

The implementation requires **GNU/Linux, Python 3.10+, NumPy and GCC with libquadmath**. No GPU is required. On Ubuntu/Debian, install `g++` if absent.

```bash
git clone https://github.com/OliverDOU776/Transporting-Root-Evidence-for-Repeated-Adsorption-Ranking.git
cd Transporting-Root-Evidence-for-Repeated-Adsorption-Ranking
python -m venv .venv
source .venv/bin/activate
python -m pip install .
python examples/repeated_ranking.py
```

The native library compiles on first use into the user cache. `ROOT_TRANSPORT_CACHE` selects another cache directory.

## Usage

```python
from root_transport import StreamRanker, load_corpus

curves, pairs, metadata = load_corpus("corpus.json")
with StreamRanker(curves, pairs, method="transport") as ranker:
    ranker.seed(P=0.3, y=0.15)
    result = ranker.query(P=0.305, y=0.152, k=5)
    print(result)
```

`seed` acquires evidence by solving the supported source pool; this cost must be included in lifecycle comparisons. Supported stream methods are `transport`, `roots`, `cap` and `warm`. The comparison example additionally includes unseeded on-demand warm solving and the incumbent baseline.

A minimal JSON corpus is:

```json
{
  "curves": [
    {"p": [0, 0.1, 1, 10], "q": [0, 0.1, 0.8, 2]},
    {"p": [0, 0.1, 1, 10], "q": [0, 0.2, 1.2, 3]}
  ],
  "pairs": [[0, 1]]
}
```

Pressures must strictly increase. Non-origin pressures and uptakes must be positive. The caller supplies compatible pressure/uptake units; the loader performs no conversion or high-pressure extrapolation. Object-form pairs with `i`, `j`, `family` and `temperature` fields support corpus filtering and original ID mapping.

```bash
python examples/rank_corpus.py corpus.json --pressure 0.3 --feed 0.15 --top-k 1
python examples/compare_executors.py
```

## Reproducibility

```bash
python -m pip install '.[test]'
python -m pytest -q
```

Tests cover analytic Henry-law scores, support boundaries, threshold predicates, deterministic ties, invalid inputs and nonlinear stream agreement with complete solving. The six-arm comparison example checks all returned outputs on a common workload. The native mathematical kernel is retained from the paper implementation, with packaging and lifecycle handling around it.

The demonstration inputs, recording details and encoding instructions are provided in [docs/media/README.md](docs/media/README.md). CRAFTED/NIST curve snapshots are not bundled; the loader also accepts the paper companion's processed corpus schema. The repository provides functional code and compact derived results, without internal run logs or research administration records. The included synthetic demonstrations and functional checks are separate from reproduction of the complete paper campaign.

| Directory | Contents |
|---|---|
| `src/root_transport/` | Native numerical engine and Python API |
| `examples/` | Repeated-query and matched-executor examples |
| `scripts/` | Reproducible demonstration generation |
| `tests/` | Analytic and nonlinear functional checks |
| `docs/` | GitHub Pages source, paper, figures and videos |
| `evidence/` | Curated publication-level result summaries |

The numerical tests have finite coverage. They do not establish all-domain floating-point soundness, experimental IAST accuracy or physical validation. See the paper for the full model and evaluation scope.

## Citation

```bibtex
@misc{wang2026transporting,
  title  = {Transporting Root Evidence for Repeated Adsorption Ranking},
  author = {Wang, Zijia and Hong, Haoliang and Li, Xuhui and Bai, Jingyang and Nie, Binjian},
  year   = {2026},
  url    = {https://github.com/OliverDOU776/Transporting-Root-Evidence-for-Repeated-Adsorption-Ranking}
}
```

## Attribution

Software and manuscript: <p><a href="mailto:zijia.wang@said.oxford.edu">Zijia Wang</a><sup>∗</sup>, <a href="mailto:haoliang.hong@eng.ox.ac.uk">Haoliang Hong</a><sup>∗</sup>, <a href="mailto:lixuhui25@mails.ucas.ac.cn">Xuhui Li</a><sup>†</sup>, <a href="mailto:j.bai22@imperial.ac.uk">Jingyang Bai</a><sup>‡</sup>, <a href="mailto:binjian.nie@eng.ox.ac.uk">Binjian Nie</a><sup>∗</sup></p>

<sup>∗</sup>University of Oxford, United Kingdom · <sup>†</sup>University of Chinese Academy of Sciences, China · <sup>‡</sup>Imperial College London, United Kingdom

<details><summary>Author contact</summary>

Zijia Wang: [zijia.wang@said.oxford.edu](mailto:zijia.wang@said.oxford.edu)

Haoliang Hong: [haoliang.hong@eng.ox.ac.uk](mailto:haoliang.hong@eng.ox.ac.uk)

Xuhui Li: [lixuhui25@mails.ucas.ac.cn](mailto:lixuhui25@mails.ucas.ac.cn)

Jingyang Bai: [j.bai22@imperial.ac.uk](mailto:j.bai22@imperial.ac.uk)

Binjian Nie: [binjian.nie@eng.ox.ac.uk](mailto:binjian.nie@eng.ox.ac.uk)

</details>. Third-party adaptations retain their upstream notices; see [NOTICE.md](NOTICE.md). The project page is an original implementation informed by the organization of [VGGT](https://vgg-t.github.io/), [ReAct](https://react-lm.github.io/), [WebArena](https://webarena.dev/og/) and [Self-Refine](https://selfrefine.info/).

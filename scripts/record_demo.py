"""Regenerate the small, verified native-query replay used by the project page.

The input pool is synthetic and deterministic. This script records selected
numerical outputs and work counters; it does not measure or claim speedup.
Install the package first, then run ``python scripts/record_demo.py``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from root_transport import IASTEngine, StreamRanker
import root_transport

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))
from repeated_ranking import demo_pool


STATES = ((.3, .15), (.32, .16), (.1, .3), (1., .5), (2., .9), (.01, .01))
COUNTERS = ("root_solves", "pi_probes", "pairs_seen", "supported",
            "threshold_tests", "anchor_tests", "anchor_rejected",
            "history_needed_rejected", "cap_tail_rejected")


def counters(result):
    return {key: int(result["stats"][key]) for key in COUNTERS}


def record():
    curves, pairs = demo_pool()
    corpus = {"curves": [{"p": c["p"].tolist(), "q": c["q"].tolist()} for c in curves],
              "pairs": pairs.tolist()}
    encoded_corpus = json.dumps(corpus, sort_keys=True, separators=(",", ":"),
                                allow_nan=False).encode()
    records = []
    with StreamRanker(curves, pairs, method="transport", tol=1e-12) as transport, \
            IASTEngine(curves, pairs) as full:
        setup = {"transport_pi_probes": int(transport.engine.build_stats["inverse_probes"]),
                 "reference_pi_probes": int(full.build_stats["inverse_probes"])}
        seed = transport.seed(P=.3, y=.15)
        acquisition = {"pressure": .3, "feed": .15, "requested_k": len(pairs),
                       "returned_candidates": len(seed["pair_indices"]),
                       **counters(seed)}
        t_roots, f_roots = acquisition["root_solves"], 0
        t_probes = setup["transport_pi_probes"] + acquisition["pi_probes"]
        f_probes = setup["reference_pi_probes"]
        previous = None
        for index, (pressure, feed) in enumerate(STATES, 1):
            result = transport.query(P=pressure, y=feed, k=5)
            reference = full.query(pressure, feed, 5, "full", tol=1e-12)
            np.testing.assert_array_equal(result["pair_indices"], reference["pair_indices"])
            np.testing.assert_allclose(result["scores"], reference["scores"],
                                       rtol=1e-10, atol=1e-12)
            winner_ids = result["pair_indices"].tolist()
            t_count, f_count = counters(result), counters(reference)
            t_roots += t_count["root_solves"]
            f_roots += f_count["root_solves"]
            t_probes += t_count["pi_probes"]
            f_probes += f_count["pi_probes"]
            records.append({
                "index": index, "pressure": pressure, "feed": feed, "k": 5,
                "winner_ids": winner_ids, "scores": result["scores"].tolist(),
                "score_lower": result["score_lower"].tolist(),
                "score_upper": result["score_upper"].tolist(),
                "supported_candidates": int(reference["stats"]["supported"]),
                "transport": t_count, "full_reference": f_count,
                "cumulative_root_solves_including_acquisition": {
                    "transport": t_roots, "full_reference": f_roots},
                "cumulative_pi_probes_including_setup_and_acquisition": {
                    "transport": t_probes, "full_reference": f_probes},
                "matches_reference": True,
                "ranking_changed": previous is not None and winner_ids != previous,
            })
            previous = winner_ids
    assert any(row["ranking_changed"] for row in records)
    native = Path(root_transport.__file__).parent / "native" / "iast_engine.cpp"
    return {
        "schema_version": 1,
        "kind": "native_engine_synthetic_query_replay",
        "scope": "Illustrative synthetic finite-support PWL curves; not paper benchmark data or experimental chemistry.",
        "playback_note": "Animation pacing is illustrative, not elapsed execution time. No timing measurements are recorded.",
        "numerical_note": "Top-k ids match full solving exactly under the shared deterministic boundary policy; scores match within rtol=1e-10, atol=1e-12. This finite check is not a global soundness proof.",
        "counter_note": "pi_probes counts scalar or bounded spreading-pressure API calls, not time or transcendental operations. Bounded calls can evaluate two endpoints across knots. supported_candidates comes from the full scan; transport.supported counts only candidates visited by that executor. Setup probes and full acquisition are included in cumulative counters. The source wrapper names its setup counter inverse_probes because those calls arise during inverse construction.",
        "generator": {"name": "examples/repeated_ranking.py:demo_pool", "rng": "numpy.default_rng", "seed": 9182,
                      "curves": len(curves), "pairs": len(pairs), "pressure_knots_per_curve": 31,
                      "pressure_unit": "arbitrary consistent synthetic pressure unit",
                      "uptake_unit": "arbitrary consistent synthetic uptake unit"},
        "native_source_sha256": hashlib.sha256(native.read_bytes()).hexdigest(),
        "corpus_sha256": hashlib.sha256(encoded_corpus).hexdigest(),
        "corpus": corpus,
        "setup": setup,
        "acquisition": acquisition,
        "queries": records,
        "verification": {"queries_checked": len(records), "all_topk_ids_match": True,
                         "all_scores_match": True,
                         "ranking_changes": sum(row["ranking_changed"] for row in records)},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/media/query-replay-data.json")
    args = parser.parse_args()
    data = record()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    print(f"Recorded {data['verification']['queries_checked']} verified native queries; "
          f"{data['verification']['ranking_changes']} ranking changes → {args.output}")


if __name__ == "__main__":
    main()

"""Compare complete executor lifecycles on synthetic or caller-supplied data.

This compact runner is for local exploration, not a replay of the paper's
frozen campaigns. All methods share one preloaded native library. Each clock
includes construction, indexing, acquisition when applicable, queries, and
teardown. It excludes data loading, native compilation, and output checks.
Six arms include seeded WarmCap and unseeded WarmOnDemand separately.
"""
import argparse
import json
import time
import numpy as np
from root_transport import IASTEngine, load_corpus
from root_transport.engine import _library
from repeated_ranking import demo_pool


def compare(curves, pairs, queries, k, seed=(.3, .15)):
    _library()  # Common one-time compile/load excluded from each arm's clock.
    with IASTEngine(curves, pairs) as reference:
        expected = [reference.query(P, y, k, "full", tol=1e-12) for P, y in queries]
    rows = []
    arms = {"incumbent": ("continuation", False), "lean_cap": ("indexed_cap", False),
            "roots": ("indexed_roots", True), "transport": ("indexed_transport", True),
            "warm_cap": ("indexed_warm", True),
            "warm_on_demand": ("indexed_warm", False)}
    for name, (method, seeded) in arms.items():
        begin = time.perf_counter()
        engine = IASTEngine(curves, pairs, lean_cap=name == "lean_cap")
        try:
            if method.startswith("indexed_"):
                engine.prepare_cap_index()
            previous = np.empty(0, dtype=np.int64)
            seed_result = engine.query(*seed, len(pairs), "warm_full", tol=1e-12) if seeded else None
            if seed_result is not None:
                previous = seed_result["pair_indices"][:k]
            outputs = []
            for P, y in queries:
                order = previous
                if method == "continuation":
                    mask = np.ones(len(pairs), dtype=bool)
                    mask[previous] = False
                    order = np.concatenate((previous, np.flatnonzero(mask)))
                result = engine.query(P, y, k, method, order=order, tol=1e-12)
                previous = result["pair_indices"]
                outputs.append(result)
        finally:
            engine.close()
        elapsed = time.perf_counter() - begin
        for got, target in zip(outputs, expected):
            np.testing.assert_array_equal(got["pair_indices"], target["pair_indices"])
            np.testing.assert_allclose(got["scores"], target["scores"], rtol=1e-8, atol=1e-10)
        counted = outputs + ([] if seed_result is None else [seed_result])
        rows.append({"executor": name, "paid_seconds": elapsed,
                     "root_solves_including_acquisition": sum(r["stats"]["root_solves"] for r in counted),
                     "inverse_probes_including_setup": engine.build_stats["inverse_probes"]
                         + sum(r["stats"]["pi_probes"] for r in counted),
                     "all_outputs_match_reference": True})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", help="Optional curve/pair JSON; defaults to synthetic curves")
    parser.add_argument("--family")
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--queries", help='JSON list of {"P": pressure, "y": feed} states')
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--seed-pressure", type=float, default=.3)
    parser.add_argument("--seed-feed", type=float, default=.15)
    args = parser.parse_args()
    if args.corpus:
        curves, pairs, _ = load_corpus(args.corpus, family=args.family, temperature=args.temperature)
    else:
        curves, pairs = demo_pool()
    if args.queries:
        from pathlib import Path
        states = json.loads(Path(args.queries).read_text())
        queries = [(q["P"], q["y"]) for q in states]
    else:
        queries = [(.3+.005*i, .15+.002*i) for i in range(16)]
    print(json.dumps({"scope": "local exploratory lifecycle comparison; not paper benchmark",
                      "source": args.corpus or "synthetic", "pairs": len(pairs), "queries": len(queries),
                      "results": compare(curves, pairs, queries, args.top_k,
                                         seed=(args.seed_pressure, args.seed_feed))}, indent=2))


if __name__ == "__main__":
    main()

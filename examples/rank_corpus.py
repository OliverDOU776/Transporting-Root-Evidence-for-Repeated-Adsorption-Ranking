"""Rank a caller-supplied corpus; run with --help for the JSON interface."""
import argparse
import json
from root_transport import StreamRanker, load_corpus


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", help="JSON containing curves and pairs")
    parser.add_argument("--family", help="Exact pair metadata family, e.g. CO2/N2")
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--pressure", type=float, required=True)
    parser.add_argument("--feed", type=float, required=True, help="Mole fraction of first gas")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--seed-pressure", type=float)
    parser.add_argument("--seed-feed", type=float)
    args = parser.parse_args()
    if (args.seed_pressure is None) != (args.seed_feed is None):
        parser.error("Pass --seed-pressure and --seed-feed together")
    curves, pairs, metadata = load_corpus(args.corpus, family=args.family, temperature=args.temperature)
    with StreamRanker(curves, pairs) as ranker:
        if args.seed_pressure is not None:
            ranker.seed(args.seed_pressure, args.seed_feed)
        result = ranker.query(args.pressure, args.feed, args.top_k)
        winners = [dict(source_pair_id=metadata["source_pair_ids"][int(i)],
                        curve_ids=pairs[i].tolist(), selectivity=float(s),
                        lower=float(lo), upper=float(hi))
                   for i, s, lo, hi in zip(result["pair_indices"], result["scores"],
                                           result["score_lower"], result["score_upper"])]
    print(json.dumps({"winners": winners, "work_counters": result["stats"]}, indent=2))


if __name__ == "__main__":
    main()

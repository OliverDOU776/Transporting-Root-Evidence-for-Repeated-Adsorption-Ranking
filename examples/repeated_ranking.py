"""Small synthetic demonstration; timings are not the paper's benchmark."""
import numpy as np
from root_transport import IASTEngine, StreamRanker


def demo_pool():
    rng = np.random.default_rng(9182)
    pressure = np.geomspace(1e-3, 100, 31)
    curves = []
    for _ in range(24):
        capacity = rng.uniform(.2, 10)
        affinity = 10 ** rng.uniform(-2, 2)
        uptake = capacity * affinity * pressure / (1 + affinity * pressure)
        curves.append({"p": pressure, "q": uptake})
    pairs = np.array([(i, j) for i in range(12) for j in range(12, 24)])
    return curves, pairs


def main():
    curves, pairs = demo_pool()
    print("Synthetic finite-support PWL example | 144 curve pairs | top-5")
    with StreamRanker(curves, pairs) as ranker, IASTEngine(curves, pairs) as reference:
        seed = ranker.seed(P=.3, y=.15)
        print(f"Acquisition: {seed['stats']['root_solves']} root solves")
        for pressure, feed in ((.3, .15), (.305, .152), (.31, .154), (.32, .16)):
            result = ranker.query(P=pressure, y=feed, k=5)
            expected = reference.query(pressure, feed, 5, "full", tol=1e-12)
            np.testing.assert_array_equal(result["pair_indices"], expected["pair_indices"])
            np.testing.assert_allclose(result["scores"], expected["scores"], rtol=1e-10)
            print(f"P={pressure:.3f}, y={feed:.3f} | winners={result['pair_indices'].tolist()} "
                  f"| root solves={result['stats']['root_solves']} | reference match=True")
    print("All repeated-query outputs match the full-solve reference.")


if __name__ == "__main__":
    main()

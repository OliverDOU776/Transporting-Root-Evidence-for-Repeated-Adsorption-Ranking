"""Functional checks against analytic answers and an independent full-solve arm."""
import json
import numpy as np
import pytest
from root_transport import IASTEngine, StreamRanker, load_corpus


@pytest.fixture
def henry_pool():
    p = np.array([0., .01, .1, 1., 10., 100.])
    return [(p, 2*p), (p, p), (p, 5*p), (p, .2*p)], np.array([[0, 1], [2, 1], [0, 3], [2, 3], [1, 0]])


def test_analytic_henry_scores_thresholds_and_support(henry_pool):
    curves, pairs = henry_pool
    with IASTEngine(curves, pairs) as engine:
        for feed in (.01, .15, .5, .99):
            for i, truth in enumerate((2., 5., 10., 25., .5)):
                solved = engine.solve_pair(i, .1, feed, tol=1e-12)
                assert np.isclose(solved["score"], truth, rtol=1e-10)
                assert solved["lower"] <= truth <= solved["upper"]
                assert engine.threshold_test(i, .1, feed, truth*.9)["comparison"] == 1
                assert engine.threshold_test(i, .1, feed, truth*1.1)["comparison"] == -1
        cap = engine.max_pressure(.5)[0]
        assert engine.solve_pair(0, cap*(1-1e-10), .5) is not None
        assert engine.solve_pair(0, cap*(1+1e-10), .5) is None


@pytest.mark.parametrize("method", ["transport", "roots", "cap", "warm"])
def test_repeated_nonlinear_outputs_match_full_reference(method):
    rng = np.random.default_rng(9182)
    pp = np.geomspace(.001, 100., 31)
    curves = []
    for _ in range(24):
        capacity, affinity = rng.uniform(.2, 10), 10**rng.uniform(-2, 2)
        curves.append((pp, capacity*affinity*pp/(1+affinity*pp)))
    pairs = np.array([(i, j) for i in range(12) for j in range(12, 24)])
    with StreamRanker(curves, pairs, method=method) as stream, IASTEngine(curves, pairs) as reference:
        stream.seed(.3, .15)
        for P, y, k in ((.3, .15, 1), (.305, .152, 10), (.1, .3, 5), (1., .5, 20), (2., .9, 5)):
            got = stream.query(P, y, k)
            expected = reference.query(P, y, k, "full", tol=1e-12)
            np.testing.assert_array_equal(got["pair_indices"], expected["pair_indices"])
            np.testing.assert_allclose(got["scores"], expected["scores"], rtol=1e-10)
            assert np.all(got["score_lower"] <= got["scores"])
            assert np.all(got["score_upper"] >= got["scores"])


def test_deterministic_boundary_tie():
    p = np.array([0., .01, .1, 1., 10., 100.])
    with IASTEngine([(p, (2-1e-9)*p), (p, 2*p), (p, p)], [[0, 2], [1, 2]]) as e:
        e.prepare_cap_index()
        for method in ("full", "threshold", "indexed_transport"):
            assert e.query(.1, .5, 1, method)["pair_indices"].tolist() == [0]


def test_safe_lifecycle_and_invalid_inputs(henry_pool):
    curves, pairs = henry_pool
    with IASTEngine(curves, pairs) as engine:
        for P, y in ((0., .5), (1., 0.), (float("nan"), .5), (1., float("inf"))):
            with pytest.raises(ValueError):
                engine.query(P, y, 1)
        with pytest.raises(ValueError):
            engine.query(.1, .5, 1.5)
        with pytest.raises(ValueError):
            engine.solve_pair(-1, .1, .5)
    engine.close()
    with pytest.raises(RuntimeError, match="closed"):
        engine.query(.1, .5, 1)
    with pytest.raises(RuntimeError, match="closed"):
        engine.reset_anchors()
    with pytest.raises(ValueError):
        IASTEngine(curves, [[0.5, 1.]])


def test_json_corpus_filter_and_id_mapping(tmp_path):
    corpus = {"curves": [{"p": [.1, 1], "q": [.2, 2]}, {"p": [.1, 1], "q": [.1, 1]}],
              "pairs": [{"i": 0, "j": 1, "family": "CO2/N2", "temperature": 298.},
                        {"i": 1, "j": 0, "family": "CO2/CH4", "temperature": 298.}]}
    path = tmp_path / "curves.json"
    path.write_text(json.dumps(corpus))
    curves, pairs, metadata = load_corpus(path, family="CO2/N2", temperature=298.)
    assert pairs.tolist() == [[0, 1]]
    assert metadata["source_pair_ids"] == [0]
    with IASTEngine(curves, pairs) as engine:
        assert engine.query(.1, .5, 1)["pair_indices"].tolist() == [0]

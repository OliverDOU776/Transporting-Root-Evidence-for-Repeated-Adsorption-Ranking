"""Small stateful interface matching the paper's seed-and-reuse execution."""
from __future__ import annotations
import numpy as np
from .engine import IASTEngine


class StreamRanker:
    """Rank related pressure/feed queries while retaining numerical evidence.

    Call ``seed(P, y)`` to acquire roots for all supported candidates. Subsequent
    ``query`` calls transport root intervals and negative cut witnesses, with
    previous winners visited first. Evidence is tied to this fixed curve pool.
    Construction, indexing, and acquisition have real costs; benchmark the
    complete lifecycle when comparing against another executor.
    """
    def __init__(self, curves, pairs, *, method="transport", tol=1e-12):
        methods = {"transport": "indexed_transport", "roots": "indexed_roots",
                   "cap": "indexed_cap", "warm": "indexed_warm"}
        if method not in methods:
            raise ValueError(f"method must be one of {tuple(methods)}")
        if not np.isfinite(tol) or tol <= 0:
            raise ValueError("tol must be finite and positive")
        self.engine = IASTEngine(curves, pairs, lean_cap=method == "cap")
        self.engine.prepare_cap_index()
        self.method = methods[method]
        self.tol = tol
        self.previous = np.empty(0, dtype=np.int64)

    def seed(self, P, y):
        """Acquire one scored root interval per supported pair; return results."""
        acquisition = "full" if self.engine.lean_cap else "warm_full"
        result = self.engine.query(P, y, len(self.engine.pairs), acquisition, tol=self.tol)
        self.previous = result["pair_indices"].copy()
        return result

    def query(self, P, y, k):
        """Return ordered pair indices, selectivity brackets, and work counters."""
        # The full acquisition is used only for evidence; the incumbent prefix
        # for the first top-k query follows the benchmark's seed[:k] convention.
        result = self.engine.query(P, y, k, self.method,
                                   order=self.previous[:k], tol=self.tol)
        self.previous = result["pair_indices"].copy()
        return result

    def close(self):
        self.engine.close()

    def __enter__(self):
        self.engine._require_open()
        return self

    def __exit__(self, *exc):
        self.close()

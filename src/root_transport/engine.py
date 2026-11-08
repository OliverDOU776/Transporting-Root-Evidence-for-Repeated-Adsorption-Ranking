"""Finite-support binary IAST engine with transported root evidence.

Numerical equivalence, not an empirical uncertainty/physical-validity certificate.
An explicit straight line to the origin is part of every model. No high-pressure
extrapolation is used. ``full`` and ``threshold`` use an identical root solver.
"""
from __future__ import annotations

import ctypes as ct
import json
from pathlib import Path
import time
import numpy as np
from ._build import native_library_path


class _Stats(ct.Structure):
    _fields_ = [(name, ct.c_uint64) for name in (
        "pairs_seen", "supported", "support_rejected", "root_solves", "pi_probes",
        "iterations", "threshold_tests", "threshold_rejected", "domain_rejected",
        "near_tie_fallbacks", "support_refinements", "boundary_tie_candidates",
        "anchor_tests", "anchor_rejected", "anchor_updates", "warm_brackets", "warm_fallbacks",
        "continuations", "legacy_refresh_items", "witness_updates", "invalid_anchors",
        "ruptura_attempts", "ruptura_iterations", "ruptura_fallbacks", "ruptura_warm_starts", "rank_witness_candidates", "canonical_refinements", "precision_fallbacks", "ruptura_boundary_fallbacks")] + [("seconds", ct.c_double)] + [(name, ct.c_uint64) for name in (
        "cap_sufficient_rejected", "history_needed_rejected", "origin_solved_tests",
        "origin_witness_tests", "origin_mixed_tests", "interval_samples", "cap_tail_rejected")] + [
        ("cap_fraction_width_sum",ct.c_double),("final_fraction_width_sum",ct.c_double)]

    def as_dict(self):
        return {name: getattr(self, name) for name, _ in self._fields_}


_LIB = None


def _library():
    global _LIB
    if _LIB is not None:
        return _LIB
    target = native_library_path()
    lib = ct.CDLL(str(target))
    ip = ct.POINTER(ct.c_int64)
    dp = ct.POINTER(ct.c_double)
    ep = ct.POINTER(ct.c_char)
    sp = ct.POINTER(_Stats)
    lib.iast_create.argtypes = [ct.c_int64, ip, dp, dp, ct.c_int64, ip, ep, ct.c_int64]
    lib.iast_create.restype = ct.c_void_p
    lib.iast_create_lean_cap.argtypes=lib.iast_create.argtypes
    lib.iast_create_lean_cap.restype=ct.c_void_p
    lib.iast_set_bounds_mode.argtypes=[ct.c_void_p,ct.c_int]
    lib.iast_owned_bytes.argtypes=[ct.c_void_p,ct.POINTER(ct.c_uint64)]
    lib.iast_audit_intervals.argtypes=[ct.c_void_p,ct.c_double,ct.c_double,ep,ct.c_int64,ep,ct.c_int64]
    lib.iast_audit_intervals.restype=ct.c_int64
    lib.iast_destroy.argtypes = [ct.c_void_p]
    lib.iast_reset_anchors.argtypes = [ct.c_void_p]
    lib.iast_set_anchor_updates.argtypes = [ct.c_void_p, ct.c_int]
    lib.iast_prepare_cap_index.argtypes = [ct.c_void_p]
    lib.iast_index_bytes.argtypes = [ct.c_void_p]
    lib.iast_index_bytes.restype = ct.c_uint64
    lib.iast_set_incumbents.argtypes = [ct.c_void_p,ip,ct.c_int64]
    lib.iast_set_diagnostics.argtypes = [ct.c_void_p,ct.c_int]
    lib.iast_anchor_inventory.argtypes = [ct.c_void_p,ct.POINTER(ct.c_uint64)]
    lib.iast_anchor_bytes.argtypes = [ct.c_void_p]
    lib.iast_anchor_bytes.restype = ct.c_uint64
    lib.iast_metadata.argtypes = [ct.c_void_p, dp, dp, ct.POINTER(ct.c_uint64)]
    lib.iast_query.argtypes = [ct.c_void_p, ct.c_double, ct.c_double, ct.c_int64, ct.c_int,
                              ip, ct.c_double, ip, dp, dp, dp, sp, ep, ct.c_int64]
    lib.iast_query.restype = ct.c_int64
    lib.iast_solve_pair.argtypes = [ct.c_void_p, ct.c_int64, ct.c_double, ct.c_double,
                                   ct.c_double, dp, sp, ep, ct.c_int64]
    lib.iast_threshold.argtypes = [ct.c_void_p, ct.c_int64, ct.c_double, ct.c_double,
                                  ct.c_double, sp, ep, ct.c_int64]
    _LIB = lib
    return lib


def _ptr(arr, dtype):
    return arr.ctypes.data_as(ct.POINTER(dtype))


class IASTEngine:
    """Build from ``curves=[{'p':..., 'q':...}, ...]`` and N-by-2 pair ids.

    Pressure arrays must be strictly increasing; non-origin pressures and
    uptakes must be positive. Uptake monotonicity is not required. All paired
    curves must already have compatible physical units and provenance.
    """
    def __init__(self, curves, pairs, *, lean_cap=False,bounds_mode='fast'):
        started = time.perf_counter()
        self._lib = _library()
        ps, qs, offsets = [], [], [0]
        for curve in curves:
            p, q = (curve["p"], curve["q"]) if isinstance(curve, dict) else curve
            p, q = np.asarray(p, dtype=np.float64), np.asarray(q, dtype=np.float64)
            if p.ndim != 1 or q.ndim != 1 or len(p) != len(q):
                raise ValueError("Curve p/q must be equal-length one-dimensional arrays")
            ps.append(p); qs.append(q); offsets.append(offsets[-1] + len(p))
        if not ps:
            raise ValueError("At least one curve is required")
        pair_input = np.asarray(pairs)
        if pair_input.ndim != 2 or pair_input.shape[1] != 2 or pair_input.dtype.kind not in "iu":
            raise ValueError("pairs must be an integer N-by-2 array")
        self.pairs = np.ascontiguousarray(pair_input, dtype=np.int64)
        pflat, qflat = np.concatenate(ps), np.concatenate(qs)
        offsets = np.ascontiguousarray(offsets, dtype=np.int64)
        error = ct.create_string_buffer(1024)
        creator=self._lib.iast_create_lean_cap if lean_cap else self._lib.iast_create
        self.lean_cap=bool(lean_cap)
        self._handle = creator(len(ps), _ptr(offsets, ct.c_int64),
                    _ptr(pflat, ct.c_double), _ptr(qflat, ct.c_double), len(self.pairs),
                    _ptr(self.pairs, ct.c_int64), error, len(error))
        if not self._handle:
            raise ValueError(error.value.decode())
        if bounds_mode not in ('fast','generic_r3'):self.close();raise ValueError('Invalid bounds_mode')
        self.bounds_mode=bounds_mode
        self._lib.iast_set_bounds_mode(self._handle,int(bounds_mode=='fast'))
        metadata = np.empty((len(self.pairs), 3), dtype=np.float64)
        seconds, probes = ct.c_double(), ct.c_uint64()
        self._lib.iast_metadata(self._handle, _ptr(metadata, ct.c_double), ct.byref(seconds), ct.byref(probes))
        self.support_metadata = {"a1": metadata[:, 0], "a2": metadata[:, 1], "pi_cap": metadata[:, 2]}
        self.build_stats = {"native_seconds": seconds.value, "inverse_probes": probes.value,
                            "total_seconds_including_compile": time.perf_counter() - started,
                            "curves": len(ps), "pairs": len(self.pairs), "points": len(pflat)}

    def __enter__(self):
        self._require_open()
        return self

    def __exit__(self, *exc):
        self.close()

    def _require_open(self):
        if getattr(self, "_handle", None) is None:
            raise RuntimeError("Engine is closed")

    @staticmethod
    def _validate_state(P, y, tol=None):
        if not np.isfinite(P) or P <= 0 or not np.isfinite(y) or not 0 < y < 1:
            raise ValueError("Require finite P>0 and 0<y<1")
        if tol is not None and (not np.isfinite(tol) or tol <= 0):
            raise ValueError("tol must be finite and positive")

    def close(self):
        if getattr(self, "_handle", None):
            self._lib.iast_destroy(self._handle)
            self._handle = None

    def __del__(self):
        self.close()

    def set_anchor_updates(self, enabled):
        self._require_open()
        self._lib.iast_set_anchor_updates(self._handle, int(bool(enabled)))

    def prepare_cap_index(self):
        self._require_open()
        self._lib.iast_prepare_cap_index(self._handle)

    @property
    def index_bytes(self):
        self._require_open()
        return int(self._lib.iast_index_bytes(self._handle))

    def set_diagnostics(self, enabled):
        self._require_open()
        self._lib.iast_set_diagnostics(self._handle,int(bool(enabled)))

    def anchor_inventory(self):
        self._require_open()
        values=(ct.c_uint64*4)()
        self._lib.iast_anchor_inventory(self._handle,values)
        return dict(zip(("valid_slots","solved_only_slots","witness_only_slots","mixed_slots"),map(int,values)))

    def owned_bytes(self):
        self._require_open()
        values=(ct.c_uint64*7)();self._lib.iast_owned_bytes(self._handle,values)
        result=dict(zip(('curve_payload_bytes','curve_struct_bytes','pair_capacity_bytes','anchor_capacity_bytes',
                         'ruptura_state_bytes','index_capacity_bytes','engine_struct_bytes'),map(int,values)))
        result['total_owned_capacity_bytes']=sum(result.values())
        return result

    def audit_intervals(self,P,y):
        self._require_open()
        output=ct.create_string_buffer(max(4096,len(self.pairs)*2048));error=ct.create_string_buffer(1024)
        n=self._lib.iast_audit_intervals(self._handle,P,y,output,len(output),error,len(error))
        if n<0:raise RuntimeError(error.value.decode())
        return json.loads(output.value.decode())

    def reset_anchors(self):
        self._require_open()
        self._lib.iast_reset_anchors(self._handle)

    @property
    def anchor_bytes(self):
        self._require_open()
        return int(self._lib.iast_anchor_bytes(self._handle))

    def max_pressure(self, y):
        self._require_open()
        if not 0 < y < 1:
            raise ValueError("Require 0<y<1")
        return 1 / (y*self.support_metadata["a1"] + (1-y)*self.support_metadata["a2"])

    def query(self, P, y, k, method="threshold", order=None, tol=1e-10):
        """Return top-k supported pair ids and numerical score brackets.

        ``order`` must be a permutation of all pair ids. Scores sort descending,
        except for a deterministic numerical shell at the kth boundary: let t
        be the raw kth score and eps=max(1e-10,1e-8*abs(t)); retain scores above
        t+eps and fill remaining places by pair id from [t-eps,t+eps].
        ``stats.seconds`` measures native query work only. ``wall_seconds`` also
        includes Python output allocation and conversion, but not order checking.
        """
        self._require_open()
        self._validate_state(P, y, tol)
        methods = {"full": 0, "threshold": 1, "indexed": 2, "continuation": 3,
                   "warm_full": 4, "warm_threshold": 5, "bound": 6, "bound_first": 7,
                   "witness_bound": 8, "witness_first": 9, "witness_warm": 10,
                   "ruptura_full": 11, "ruptura_threshold": 12, "cap_full": 13, "cap_threshold": 14,
                   "rank_warm": 15, "rank_bound": 16, "rank_cap": 17, "rank_first": 18, "rank_roots": 19, "indexed_cap": 20, "indexed_transport": 21, "indexed_roots": 22, "indexed_first": 23, "indexed_warm": 24}
        if method not in methods:
            raise ValueError(f"Unknown method {method!r}")
        if isinstance(k, (bool, np.bool_)) or not isinstance(k, (int, np.integer)):
            raise ValueError("k must be an integer")
        k = int(k)
        if k < 0:
            raise ValueError("k must be nonnegative")
        if method.startswith("indexed_"):
            inc=np.ascontiguousarray([] if order is None else order,dtype=np.int64)
            if inc.ndim!=1 or len(np.unique(inc))!=len(inc) or np.any(inc<0) or np.any(inc>=len(self.pairs)):
                raise ValueError("indexed_cap order contains distinct valid preceding winner ids only")
            self._lib.iast_set_incumbents(self._handle,_ptr(inc,ct.c_int64),len(inc))
            order=None
        if order is not None:
            order = np.ascontiguousarray(order, dtype=np.int64)
            if order.shape != (len(self.pairs),) or not np.array_equal(np.sort(order), np.arange(len(self.pairs))):
                raise ValueError("order must be a permutation of all pair ids")
        begin = time.perf_counter()
        size = min(k, len(self.pairs))
        ids = np.empty(size, dtype=np.int64)
        score, lower, upper = (np.empty(size, dtype=np.float64) for _ in range(3))
        stats, error = _Stats(), ct.create_string_buffer(1024)
        n = self._lib.iast_query(self._handle, P, y, k, methods[method],
                   _ptr(order, ct.c_int64) if order is not None else None, tol,
                   _ptr(ids, ct.c_int64), _ptr(score, ct.c_double), _ptr(lower, ct.c_double),
                   _ptr(upper, ct.c_double), ct.byref(stats), error, len(error))
        if n < 0:
            raise RuntimeError(error.value.decode())
        result = {"pair_indices": ids[:n], "scores": score[:n], "score_lower": lower[:n],
                  "score_upper": upper[:n], "stats": stats.as_dict(), "tolerance": tol,
                  "numerical_contract": "R3 finite-validated numerical policy: direct score-pressure tri-state threshold; directed elementary bounds under stated libm assumptions; shared score-coordinate binary128 fallback; unchanged deterministic kth tolerance shell"}
        result["wall_seconds"] = time.perf_counter() - begin
        return result

    def solve_pair(self, pair_id, P, y, tol=1e-10):
        self._require_open()
        self._validate_state(P, y, tol)
        if not isinstance(pair_id, (int, np.integer)) or not 0 <= pair_id < len(self.pairs):
            raise ValueError("pair_id is outside the candidate pool")
        values, stats, error = np.empty(4), _Stats(), ct.create_string_buffer(1024)
        state = self._lib.iast_solve_pair(self._handle, pair_id, P, y, tol,
                   _ptr(values, ct.c_double), ct.byref(stats), error, len(error))
        if state < 0:
            raise RuntimeError(error.value.decode())
        if state == 0:
            return None
        return dict(zip(("score", "lower", "upper", "x"), values)) | {"stats": stats.as_dict()}

    def threshold_test(self, pair_id, P, y, tau):
        """-1 below, +1 above, 0 ambiguous, None unsupported. No root solve."""
        self._require_open()
        self._validate_state(P, y)
        if not isinstance(pair_id, (int, np.integer)) or not 0 <= pair_id < len(self.pairs):
            raise ValueError("pair_id is outside the candidate pool")
        if not np.isfinite(tau) or tau <= 0:
            raise ValueError("tau must be finite and positive")
        stats, error = _Stats(), ct.create_string_buffer(1024)
        state = self._lib.iast_threshold(self._handle, pair_id, P, y, tau,
                                         ct.byref(stats), error, len(error))
        if state == -2:
            raise RuntimeError(error.value.decode())
        return {"comparison": None if state == 2 else state, "stats": stats.as_dict()}


def smoke_test():
    """Standalone synthetic correctness checks; not a corpus experiment."""
    p = np.array([0., 0.01, 0.1, 1., 10., 100.])
    # Henry curves have exact IAST selectivity K1/K2 at every supported query.
    curves = [(p, 2*p), (p, p), (p, 5*p), (p, .2*p)]
    pairs = np.array([[0,1],[2,1],[0,3],[2,3],[1,0]])
    engine = IASTEngine(curves, pairs)
    expected = np.array([2.,5.,10.,25.,.5])
    for y in (.01,.15,.5,.99):
        for i, truth in enumerate(expected):
            got=engine.solve_pair(i,.1,y,tol=1e-12)
            assert got is not None and np.isclose(got["score"],truth,rtol=1e-10), (i,y,got)
            assert engine.threshold_test(i,.1,y,truth*.9)["comparison"] == 1
            assert engine.threshold_test(i,.1,y,truth*1.1)["comparison"] == -1
        for order in (None, np.arange(len(pairs))[::-1]):
            a=engine.query(.1,y,3,"full",order,tol=1e-12)
            b=engine.query(.1,y,3,"threshold",order,tol=1e-12)
            assert np.array_equal(a["pair_indices"],b["pair_indices"])
            assert np.allclose(a["scores"],b["scores"],rtol=1e-12)
    # Non-Henry PWL curves stress slopes and reuse; no physical result implied.
    rng=np.random.default_rng(9182)
    curves=[]
    pp=np.geomspace(.001,100.,31)
    for _ in range(40):
        cap=rng.uniform(.2,10); affinity=10**rng.uniform(-2,2)
        curves.append((pp,cap*affinity*pp/(1+affinity*pp)))
    pairs=np.array([(i,j) for i in range(20) for j in range(20,40)])
    nonlinear=IASTEngine(curves,pairs)
    for P,y in ((.01,.01),(.1,.15),(1.,.5),(2.,.9)):
        a=nonlinear.query(P,y,10,"full",tol=1e-11)
        b=nonlinear.query(P,y,10,"threshold",tol=1e-11)
        assert np.array_equal(a["pair_indices"],b["pair_indices"]), (P,y,a,b)
        assert np.allclose(a["scores"],b["scores"],rtol=1e-11)
    tie=IASTEngine([(p,(2-1e-9)*p),(p,2*p),(p,p)],[[0,2],[1,2]])
    for order in (None,np.array([1,0])):
        for method in ("full","threshold"):
            got=tie.query(.1,.5,1,method,order)
            assert got["pair_indices"].tolist()==[0], got
            assert got["stats"]["root_solves"]==2, got
    cap=engine.max_pressure(.5)[0]
    assert engine.solve_pair(0,cap*(1-1e-10),.5) is not None
    assert engine.solve_pair(0,cap*(1+1e-10),.5) is None
    return {"status":"passed", "scope":"synthetic correctness smoke only",
            "henry_pair_queries":20,"nonlinear_topk_comparisons":4,
            "near_tie_order_method_checks":4,"support_boundary_checks":2}


if __name__ == "__main__":
    import json
    print(json.dumps(smoke_test(), indent=2))

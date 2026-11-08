"""Load curve/pair JSON without changing physical units or provenance."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np


def load_corpus(path, *, family=None, temperature=None):
    """Return ``(curves, pairs, metadata)`` from a curve/pair corpus JSON.

    Curves contain ``p`` and ``q`` arrays. Pairs are either ``[i,j]`` arrays or
    objects with ``i`` and ``j`` and optional ``family``/``temperature`` fields.
    Filters require object-form pairs. Original pair ids are returned so ranked
    local ids can be mapped back to the caller's source. Units and provenance
    remain the responsibility of the dataset provider and caller.
    """
    data = json.loads(Path(path).read_text())
    curves = data["curves"]
    pairs, ids = [], []
    for i, pair in enumerate(data["pairs"]):
        if isinstance(pair, dict):
            if family is not None and pair.get("family") != family:
                continue
            if temperature is not None and pair.get("temperature") != temperature:
                continue
            pairs.append([pair["i"], pair["j"]])
        else:
            if family is not None or temperature is not None:
                raise ValueError("Filters require object-form pairs with metadata")
            pairs.append(pair)
        ids.append(i)
    source_array = np.asarray(pairs)
    if source_array.ndim != 2 or source_array.shape[1] != 2 or source_array.dtype.kind not in "iu":
        raise ValueError("Pair ids must be an integer N-by-2 array")
    array = np.asarray(source_array, dtype=np.int64)
    if not len(array):
        raise ValueError("The corpus selection has no candidate pairs")
    if np.any(array < 0) or np.any(array >= len(curves)):
        raise ValueError("Pair refers to an unknown curve id")
    return curves, array, {"source_pair_ids": ids, "source": str(path),
                           "family": family, "temperature": temperature}

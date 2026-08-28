"""noesis_harness/ordered_dict.py — ordered dict wrapper.

Patterns: LoopX ordered dict.
Stdlib only.
"""
from __future__ import annotations
from collections import OrderedDict

class OrderedMap:
    def __init__(self): self._d = OrderedDict()
    def put(self, k, v) -> None: self._d[k] = v
    def get(self, k, default=None): return self._d.get(k, default)
    def keys(self): return list(self._d.keys())
    def __contains__(self, k): return k in self._d
    def __len__(self): return len(self._d)

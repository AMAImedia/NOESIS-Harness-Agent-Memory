"""noesis_harness/comparator.py — deep structural equality.

Patterns: LoopX comparator.
Stdlib only.
"""
from __future__ import annotations
from typing import Any

def equals(a: Any, b: Any) -> bool:
    if type(a) is not type(b): return False
    if isinstance(a, dict): return len(a) == len(b) and all(equals(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)): return len(a) == len(b) and all(equals(x, y) for x, y in zip(a, b))
    if isinstance(a, (set, frozenset)): return equals(sorted(a), sorted(b))
    return a == b

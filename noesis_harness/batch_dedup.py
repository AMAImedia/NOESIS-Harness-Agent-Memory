"""noesis_harness/batch_dedup.py — batch dedup.

Patterns: LoopX batch dedup.
Stdlib only.
"""
from __future__ import annotations
from typing import List, Any

def batch_dedup(items: List[Any]) -> List[Any]:
    seen = set(); out = []
    for item in items:
        if item not in seen: seen.add(item); out.append(item)
    return out
def batch_dedup_key(items: List[Any], key_fn) -> List[Any]:
    seen = set(); out = []
    for item in items:
        k = key_fn(item)
        if k not in seen: seen.add(k); out.append(item)
    return out

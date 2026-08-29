"""noesis_harness/async_dedup.py — async dedup.

Patterns: LoopX async dedup.
Stdlib only.
"""
from __future__ import annotations
import concurrent.futures
from typing import Callable, List, Any

def parallel_dedup(fn: Callable, items: list, max_workers: int = 4) -> list:
    seen = set(); out = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        results = list(ex.map(fn, items))
    for result in results:
        if result not in seen: seen.add(result); out.append(result)
    return out

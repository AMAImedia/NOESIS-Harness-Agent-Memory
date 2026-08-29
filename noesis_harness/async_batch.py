"""noesis_harness/async_batch.py — batch operations in threads.

Patterns: LoopX async batch.
Stdlib only.
"""
from __future__ import annotations
import concurrent.futures
from typing import Any, Callable, List

def parallel_run(fns: List[Callable], max_workers: int = 4) -> List[Any]:
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        return list(ex.map(lambda fn: fn(), fns))
def parallel_map(fn: Callable, items: list, max_workers: int = 4) -> list:
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        return list(ex.map(fn, items))

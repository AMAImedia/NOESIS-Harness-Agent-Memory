"""noesis_harness/batch_retry.py — retry a batch of operations.

Patterns: LoopX batch retry.
Stdlib only.
"""
from __future__ import annotations
from typing import Any, Callable, List

def batch_retry(fns: List[Callable], max_attempts: int = 3) -> List[Any]:
    results = [None] * len(fns); failed = list(range(len(fns)))
    for attempt in range(max_attempts):
        still_failed = []
        for idx in failed:
            try: results[idx] = fns[idx]()
            except Exception: still_failed.append(idx)
        failed = still_failed
        if not failed: break
    return results

"""noesis_harness/retry_sync.py — retry without sleep.

Patterns: LoopX retry.
Stdlib only.
"""
from __future__ import annotations

def retry(fn, max_attempts: int = 3):
    last_exc = None
    for i in range(max_attempts):
        try: return fn()
        except Exception as e: last_exc = e
    raise last_exc
def retry_until(fn, predicate, max_attempts: int = 100):
    for i in range(max_attempts):
        result = fn()
        if predicate(result): return result
    raise RuntimeError("max attempts reached")

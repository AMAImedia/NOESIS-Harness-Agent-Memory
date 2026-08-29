"""noesis_harness/retry_simple.py — retry without sleep.

Patterns: LoopX retry.
Stdlib only.
"""
from __future__ import annotations

def retry(fn, max_attempts: int = 3):
    last_exc = None
    for _ in range(max_attempts):
        try: return fn()
        except Exception as e: last_exc = e
    raise last_exc

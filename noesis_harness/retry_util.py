"""noesis_harness/retry_util.py — retry with backoff.

Patterns: LoopX retry.
Stdlib only.
"""
from __future__ import annotations
import time

def retry(fn, max_attempts: int = 3, delay: float = 0.1, backoff: float = 2.0):
    last_exc = None
    for i in range(max_attempts):
        try: return fn()
        except Exception as e: last_exc = e; time.sleep(delay * (backoff ** i))
    raise last_exc

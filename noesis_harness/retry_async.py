"""noesis_harness/retry_async.py — retry with async support.

Patterns: LoopX retry.
Stdlib only.
"""
from __future__ import annotations
import time

def retry_sync(fn, max_attempts: int = 3, delay: float = 0.1, backoff: float = 2.0):
    last_exc = None
    for i in range(max_attempts):
        try: return fn()
        except Exception as e: last_exc = e; time.sleep(delay * (backoff ** i))
    raise last_exc
def retry_with_log(fn, max_attempts: int = 3, delay: float = 0.1, log_fn=None):
    last_exc = None
    for i in range(max_attempts):
        try: return fn()
        except Exception as e:
            last_exc = e
            if log_fn: log_fn(f"attempt {i+1} failed: {e}")
            time.sleep(delay)
    raise last_exc

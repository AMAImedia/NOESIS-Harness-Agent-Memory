"""noesis_harness/async_retry.py — retry with async support.

Patterns: LoopX retry async.
Stdlib only.
"""
from __future__ import annotations
import concurrent.futures

def retry_thread(fn, max_attempts: int = 3):
    last_exc = None
    for _ in range(max_attempts):
        try: return fn()
        except Exception as e: last_exc = e
    raise last_exc
def parallel_retry(fns, max_attempts: int = 3, max_workers: int = 4):
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        return [ex.submit(retry_thread, fn, max_attempts).result() for fn in fns]

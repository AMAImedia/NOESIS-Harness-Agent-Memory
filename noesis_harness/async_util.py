"""noesis_harness/async_util.py — async/sync bridge helpers.

Patterns: LoopX async util.
Stdlib only.
"""
from __future__ import annotations
import concurrent.futures

def run_sync(fn, *args, **kwargs):
    """Run a sync function in a thread pool (useful for mixing sync/async)."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(fn, *args, **kwargs).result()
def parallel_map(fn, items, max_workers: int = 4):
    """Map fn over items in parallel (sync wrapper)."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        return list(ex.map(fn, items))

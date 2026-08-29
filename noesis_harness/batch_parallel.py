"""noesis_harness/batch_parallel.py — parallel batch processing.

Patterns: LoopX batch parallel.
Stdlib only.
"""
from __future__ import annotations
import concurrent.futures
from typing import Callable, List, Any

def parallel_batch(fn: Callable, items: List[Any], batch_size: int = 100, max_workers: int = 4) -> list:
    batches = [items[i:i+batch_size] for i in range(0, len(items), batch_size)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        results = list(ex.map(lambda b: [fn(x) for x in b], batches))
    return [item for batch in results for item in batch]

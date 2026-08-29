"""noesis_harness/window_parallel.py — parallel window processing.

Patterns: LoopX window parallel.
Stdlib only.
"""
from __future__ import annotations
import concurrent.futures
from typing import List, Callable

def parallel_window(fn: Callable, items: list, window_size: int = 3, max_workers: int = 4) -> list:
    windows = [items[i:i+window_size] for i in range(len(items) - window_size + 1)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        return list(ex.map(fn, windows))

"""noesis_harness/memoize.py — simple deterministic memoize.

Patterns: LoopX caching.
Stdlib only.
"""
from __future__ import annotations
from functools import wraps
from typing import Callable, Dict, Tuple, Any

def memoize(fn: Callable) -> Callable:
    cache: Dict[Tuple, Any] = {}
    @wraps(fn)
    def wrapper(*args, **kwargs):
        key = (args, tuple(sorted(kwargs.items())))
        if key not in cache:
            cache[key] = fn(*args, **kwargs)
        return cache[key]
    wrapper.cache_clear = lambda: cache.clear()  # type: ignore
    wrapper.cache_info = lambda: dict(size=len(cache))  # type: ignore
    return wrapper

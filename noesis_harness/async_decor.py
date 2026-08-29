"""noesis_harness/async_decor.py — async decorator.

Patterns: LoopX async decor.
Stdlib only.
"""
from __future__ import annotations
import concurrent.futures
from typing import Callable, Dict, Any

class AsyncDecor:
    def __init__(self, max_workers: int = 4):
        self._max_workers = max_workers; self._data: Dict[str, Any] = {}
    def decor(self, fn: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            if key not in self._data:
                with concurrent.futures.ThreadPoolExecutor(max_workers=self._max_workers) as ex:
                    self._data[key] = ex.submit(fn, *args, **kwargs).result()
            return self._data[key]
        return wrapper
    def get(self, key, default=None): return self._data.get(key, default)
    def set(self, key, value) -> None: self._data[key] = value
    def invalidate(self, key) -> bool: return self._data.pop(key, None) is not None
    def clear(self) -> int: n = len(self._data); self._data.clear(); return n
    def __len__(self): return len(self._data)

"""noesis_harness/async_flush.py — async flush.

Patterns: LoopX async flush.
Stdlib only.
"""
from __future__ import annotations
import concurrent.futures
from typing import Callable, Dict, Any

class AsyncFlush:
    def __init__(self, max_workers: int = 4):
        self._max_workers = max_workers; self._data: Dict[str, Any] = {}
    def flush(self, key: str, compute_fn: Callable) -> Any:
        if key not in self._data:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self._max_workers) as ex:
                self._data[key] = ex.submit(compute_fn).result()
        return self._data[key]
    def get(self, key: str, default=None): return self._data.get(key, default)
    def set(self, key: str, value) -> None: self._data[key] = value
    def invalidate(self, key: str) -> bool: return self._data.pop(key, None) is not None
    def clear(self) -> int: n = len(self._data); self._data.clear(); return n
    def __len__(self): return len(self._data)

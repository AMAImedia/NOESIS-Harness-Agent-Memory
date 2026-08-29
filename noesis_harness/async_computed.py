"""noesis_harness/async_computed.py — async computed.

Patterns: LoopX async computed.
Stdlib only.
"""
from __future__ import annotations
import concurrent.futures
from typing import Callable, Dict, Any

class AsyncComputed:
    def __init__(self, max_workers: int = 4):
        self._max_workers = max_workers; self._data: Dict[str, Any] = {}; self._fns: Dict[str, Callable] = {}; self._disabled = set()
    def register(self, key: str, compute_fn: Callable) -> None:
        self._fns[key] = compute_fn
    def get(self, key: str) -> Any:
        if key in self._disabled: return None
        if key in self._data: return self._data[key]
        if key in self._fns:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self._max_workers) as ex:
                self._data[key] = ex.submit(self._fns[key]).result()
            return self._data[key]
        return None
    def invalidate(self, key: str) -> bool:
        self._disabled.add(key)
        return self._data.pop(key, None) is not None
    def clear(self) -> int: n = len(self._data); self._data.clear(); return n
    def __len__(self): return len(self._data)

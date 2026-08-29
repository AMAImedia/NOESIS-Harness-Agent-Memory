"""noesis_harness/async_factory.py — async factory.

Patterns: LoopX async factory.
Stdlib only.
"""
from __future__ import annotations
import concurrent.futures
from typing import Callable, Dict, Any

class AsyncFactory:
    def __init__(self, max_workers: int = 4):
        self._max_workers = max_workers; self._data: Dict[str, Any] = {}; self._factories: Dict[str, Callable] = {}; self._disabled = set()
    def register(self, key: str, factory_fn: Callable) -> None:
        self._factories[key] = factory_fn
    def get(self, key: str) -> Any:
        if key in self._disabled: return None
        if key not in self._data:
            if key in self._factories:
                with concurrent.futures.ThreadPoolExecutor(max_workers=self._max_workers) as ex:
                    self._data[key] = ex.submit(self._factories[key]).result()
            else: return None
        return self._data[key]
    def invalidate(self, key: str) -> bool:
        self._disabled.add(key)
        return self._data.pop(key, None) is not None
    def clear(self) -> int: n = len(self._data); self._data.clear(); return n
    def __len__(self): return len(self._data)

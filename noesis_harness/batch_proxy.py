"""noesis_harness/batch_proxy.py — batch proxy.

Patterns: LoopX batch proxy.
Stdlib only.
"""
from __future__ import annotations
from typing import Dict, Any, List

class BatchProxy:
    def __init__(self): self._data: Dict[str, Any] = {}
    def get_batch(self, keys: List[str]) -> Dict[str, Any]:
        return {k: self._data[k] for k in keys if k in self._data}
    def set_batch(self, items: Dict[str, Any]) -> None:
        self._data.update(items)
    def get(self, key: str, default=None): return self._data.get(key, default)
    def set(self, key: str, value) -> None: self._data[key] = value
    def invalidate(self, key: str) -> bool: return self._data.pop(key, None) is not None
    def clear(self) -> int: n = len(self._data); self._data.clear(); return n
    def __len__(self): return len(self._data)

"""noesis_harness/batch_flush.py — batch flush.

Patterns: LoopX batch flush.
Stdlib only.
"""
from __future__ import annotations
from typing import Dict, Any

class BatchFlush:
    def __init__(self): self._data: Dict[str, Any] = {}
    def flush_batch(self, items: Dict[str, Any]) -> Dict[str, Any]:
        out = {}
        for k, v in items.items():
            if k not in self._data: self._data[k] = v
            out[k] = self._data[k]
        return out
    def get(self, key: str, default=None): return self._data.get(key, default)
    def set(self, key: str, value) -> None: self._data[key] = value
    def invalidate(self, key: str) -> bool: return self._data.pop(key, None) is not None
    def clear(self) -> int: n = len(self._data); self._data.clear(); return n
    def __len__(self): return len(self._data)

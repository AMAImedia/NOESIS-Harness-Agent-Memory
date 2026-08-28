"""noesis_harness/registry.py — simple name registry.

Patterns: LoopX registry.
Stdlib only.
"""
from __future__ import annotations
from typing import Any, Dict

class Registry:
    def __init__(self): self._items: Dict[str, Any] = {}
    def put(self, name: str, value: Any) -> None:
        if not name: raise ValueError("name required")
        self._items[name] = value
    def get(self, name: str, default=None): return self._items.get(name, default)
    def has(self, name: str) -> bool: return name in self._items
    def keys(self): return list(self._items.keys())

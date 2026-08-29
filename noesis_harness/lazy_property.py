"""noesis_harness/lazy_property.py — lazy property descriptor.

Patterns: LoopX lazy property.
Stdlib only.
"""
from __future__ import annotations

class lazy_property:
    def __init__(self, func): self._func = func; self._attr = f"_lazy_{func.__name__}"
    def __set_name__(self, owner, name): self._attr = f"_lazy_{name}"
    def __get__(self, obj, objtype=None):
        if obj is None: return self
        if not hasattr(obj, self._attr): setattr(obj, self._attr, self._func(obj))
        return getattr(obj, self._attr)

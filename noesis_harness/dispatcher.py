"""noesis_harness/dispatcher.py — typed dispatcher.

Patterns: LoopX dispatcher.
Stdlib only.
"""
from __future__ import annotations
from typing import Callable, Dict

class Dispatcher:
    def __init__(self): self._handlers: Dict[str, Callable] = {}
    def register(self, name: str, fn: Callable) -> None:
        if not name: raise ValueError("name required")
        self._handlers[name] = fn
    def dispatch(self, name: str, *args, **kwargs):
        fn = self._handlers.get(name)
        if fn is None: raise KeyError(name)
        return fn(*args, **kwargs)
    def names(self): return list(self._handlers.keys())

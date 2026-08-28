"""noesis_harness/deque.py — bounded deque wrapper.

Patterns: LoopX deque.
Stdlib only.
"""
from __future__ import annotations
from collections import deque

class BoundedDeque:
    def __init__(self, maxlen: int = None):
        self._d = deque(maxlen=maxlen)
    def append(self, x): self._d.append(x)
    def appendleft(self, x): self._d.appendleft(x)
    def pop(self): return self._d.pop() if self._d else None
    def popleft(self): return self._d.popleft() if self._d else None
    def to_list(self): return list(self._d)
    def __len__(self): return len(self._d)

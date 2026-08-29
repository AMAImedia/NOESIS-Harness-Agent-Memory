"""noesis_harness/bucket_token.py — bucket token pool.

Patterns: LoopX bucket.
Stdlib only.
"""
from __future__ import annotations

class Bucket:
    def __init__(self, capacity: int):
        if capacity < 1: raise ValueError("capacity >=1")
        self._cap = capacity; self._tokens = 0
    def add(self, n: int = 1) -> int:
        space = self._cap - self._tokens; added = min(n, space); self._tokens += added; return added
    def take(self, n: int = 1) -> int:
        taken = min(n, self._tokens); self._tokens -= taken; return taken
    def tokens(self) -> int: return self._tokens
    def free(self) -> int: return self._cap - self._tokens
    def __len__(self): return self._tokens

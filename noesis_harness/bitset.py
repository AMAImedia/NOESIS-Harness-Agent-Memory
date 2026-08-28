"""noesis_harness/bitset.py — fixed-size bitset.

Patterns: LoopX bitset.
Stdlib only.
"""
from __future__ import annotations

class BitSet:
    def __init__(self, size: int):
        if size < 0: raise ValueError("size >=0")
        self.size = size; self._words = [0] * ((size + 63) // 64)
    def _idx(self, bit: int):
        if bit < 0 or bit >= self.size: raise IndexError("bit out of range")
        return bit // 64, bit % 64
    def set(self, bit: int) -> None:
        w, o = self._idx(bit); self._words[w] |= (1 << o)
    def clear(self, bit: int) -> None:
        w, o = self._idx(bit); self._words[w] &= ~(1 << o)
    def test(self, bit: int) -> bool:
        w, o = self._idx(bit); return bool(self._words[w] & (1 << o))
    def count(self) -> int:
        return sum(bin(w).count("1") for w in self._words)

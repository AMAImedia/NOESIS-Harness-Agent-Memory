"""noesis_harness/trie.py — prefix tree.

Patterns: LoopX trie.
Stdlib only.
"""
from __future__ import annotations
from typing import Dict, List

class Trie:
    def __init__(self): self._children: Dict[str, "Trie"] = {}; self._end = False
    def insert(self, word: str) -> None:
        node = self
        for ch in word:
            node = node._children.setdefault(ch, Trie())
        node._end = True
    def has(self, word: str) -> bool:
        node = self
        for ch in word:
            node = node._children.get(ch)
            if node is None: return False
        return node._end
    def starts_with(self, prefix: str) -> bool:
        node = self
        for ch in prefix:
            node = node._children.get(ch)
            if node is None: return False
        return True
    def count(self) -> int:
        total = 1 if self._end else 0
        for ch in self._children.values(): total += ch.count()
        return total

"""noesis_harness/skip_list.py — sorted skip list.

Patterns: LoopX skip list.
Stdlib only.
"""
from __future__ import annotations
import random
from typing import List, Any

_MAX_LEVEL = 16

class _Node:
    __slots__ = ("val", "next")
    def __init__(self, val: Any, height: int):
        self.val = val
        self.next = [None] * height

class SkipList:
    def __init__(self, seed: int = 0):
        self._rng = random.Random(seed)
        self._head = _Node(None, _MAX_LEVEL)
    def _random_level(self) -> int:
        lvl = 1
        while self._rng.random() < 0.5 and lvl < _MAX_LEVEL: lvl += 1
        return lvl
    def insert(self, val: Any) -> None:
        update = [self._head] * _MAX_LEVEL
        cur = self._head
        for i in range(_MAX_LEVEL - 1, -1, -1):
            while cur.next[i] is not None and cur.next[i].val < val: cur = cur.next[i]
            update[i] = cur
        nxt = cur.next[0]
        if nxt is not None and nxt.val == val: return
        node = _Node(val, self._random_level())
        for i in range(len(node.next)):
            node.next[i] = update[i].next[i]
            update[i].next[i] = node
    def __contains__(self, val: Any) -> bool:
        cur = self._head
        for i in range(_MAX_LEVEL - 1, -1, -1):
            while cur.next[i] is not None and cur.next[i].val < val: cur = cur.next[i]
        nxt = cur.next[0]
        return nxt is not None and nxt.val == val
    def to_list(self) -> List:
        out = []; cur = self._head.next[0]
        while cur is not None: out.append(cur.val); cur = cur.next[0]
        return out

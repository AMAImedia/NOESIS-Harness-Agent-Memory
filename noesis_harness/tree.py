"""noesis_harness/tree.py — n-ary tree.

Patterns: LoopX tree.
Stdlib only.
"""
from __future__ import annotations
from typing import Any, List

class TreeNode:
    def __init__(self, value: Any):
        self.value = value; self.children: List["TreeNode"] = []
    def add(self, child: "TreeNode") -> None: self.children.append(child)
    def find(self, value: Any) -> "TreeNode":
        if self.value == value: return self
        for c in self.children:
            r = c.find(value)
            if r is not None: return r
        return None
    def size(self) -> int:
        return 1 + sum(c.size() for c in self.children)

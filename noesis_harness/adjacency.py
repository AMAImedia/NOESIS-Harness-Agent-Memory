"""noesis_harness/adjacency.py — adjacency list graph.

Patterns: LoopX adjacency list.
Stdlib only.
"""
from __future__ import annotations
from collections import defaultdict

class AdjacencyList:
    def __init__(self): self._adj = defaultdict(set)
    def add_edge(self, u, v) -> None:
        self._adj[u].add(v); self._adj[v].add(u)
    def neighbors(self, u): return list(self._adj.get(u, ()))
    def nodes(self): return list(self._adj.keys())
    def __contains__(self, u): return u in self._adj

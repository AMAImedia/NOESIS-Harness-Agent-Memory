"""noesis_harness/bfs.py — BFS on adjacency dict.

Patterns: LoopX BFS.
Stdlib only.
"""
from __future__ import annotations
from collections import deque
from typing import Dict, List

def bfs(graph: Dict[str,List[str]], start: str) -> List[str]:
    if start not in graph: return []
    vis=set([start]); q=deque([start]); out=[]
    while q:
        n=q.popleft(); out.append(n)
        for nb in graph.get(n,[]):
            if nb not in vis: vis.add(nb); q.append(nb)
    return out

"""noesis_harness/dfs.py — DFS iterative.

Patterns: LoopX DFS.
Stdlib only.
"""
from __future__ import annotations
from typing import Dict, List

def dfs(graph: Dict[str,List[str]], start: str) -> List[str]:
    if start not in graph: return []
    vis=set(); stack=[start]; out=[]
    while stack:
        n=stack.pop()
        if n in vis: continue
        vis.add(n); out.append(n)
        for nb in reversed(graph.get(n,[])):
            if nb not in vis: stack.append(nb)
    return out

"""noesis_harness/topo_sort.py — Kahn topological sort.

Patterns: LoopX topo sort.
Stdlib only.
"""
from __future__ import annotations
from collections import defaultdict, deque
from typing import Dict, List

def topo_sort(nodes: List[str], edges: List[tuple]) -> List[str]:
    indeg = {n:0 for n in nodes}
    g = defaultdict(list)
    for u,v in edges:
        g[u].append(v); indeg[v] = indeg.get(v,0)+1
        if u not in indeg: indeg[u]=indeg.get(u,0)
    q = deque([n for n,d in indeg.items() if d==0])
    out=[]
    while q:
        n=q.popleft(); out.append(n)
        for nb in g[n]:
            indeg[nb]-=1
            if indeg[nb]==0: q.append(nb)
    if len(out)!=len(indeg): raise ValueError("cycle")
    # keep original nodes order filter
    return [x for x in out if x in nodes]

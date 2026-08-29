"""noesis_harness/union_find.py — Disjoint Set Union.

Patterns: LoopX DSU.
Stdlib only.
"""
from __future__ import annotations

class DSU:
    def __init__(self): self.p={}; self.r={}
    def make(self, x):
        if x not in self.p: self.p[x]=x; self.r[x]=0
    def find(self, x):
        self.make(x)
        if self.p[x]!=x: self.p[x]=self.find(self.p[x])
        return self.p[x]
    def union(self, a,b):
        ra=self.find(a); rb=self.find(b)
        if ra==rb: return False
        if self.r[ra]<self.r[rb]: self.p[ra]=rb
        elif self.r[ra]>self.r[rb]: self.p[rb]=ra
        else: self.p[rb]=ra; self.r[ra]+=1
        return True
    def connected(self,a,b): return self.find(a)==self.find(b)

"""noesis_harness/memoize_scope.py — scoped memoize.

Patterns: LoopX memoize scope.
Stdlib only.
"""
from __future__ import annotations
from typing import Dict, Any

class MemoScope:
    def __init__(self): self._scopes: Dict[str, Dict] = {}
    def scope(self, name: str) -> Dict:
        if name not in self._scopes: self._scopes[name] = {}
        return self._scopes[name]
    def get(self, scope: str, key: str, default=None):
        return self._scopes.get(scope, {}).get(key, default)
    def put(self, scope: str, key: str, value) -> None:
        self.scope(scope)[key] = value
    def invalidate_scope(self, name: str) -> int:
        return len(self._scopes.pop(name, {}))
    def invalidate_key(self, scope: str, key: str) -> bool:
        return self._scopes.get(scope, {}).pop(key, None) is not None
    def clear(self) -> int: n = sum(len(v) for v in self._scopes.values()); self._scopes.clear(); return n
    def __len__(self): return sum(len(v) for v in self._scopes.values())

"""noesis_harness/secret_store.py — in-memory secret store with redaction.

Patterns: LoopX secret handling (never log raw).
Stdlib only.
"""
from __future__ import annotations

class SecretStore:
    def __init__(self):
        self._m = {}
    def put(self, key: str, value: str) -> None:
        self._m[key] = value
    def get(self, key: str):
        return self._m.get(key)
    def redacted(self, key: str) -> str:
        v = self._m.get(key)
        if v is None: return ""
        if len(v) <= 4: return "***"
        return v[:2] + "***" + v[-2:]
    def keys(self): return list(self._m.keys())

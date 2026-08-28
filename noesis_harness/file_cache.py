"""noesis_harness/file_cache.py — read-once file content cache.

Patterns: LoopX file cache.
Stdlib only.
"""
from __future__ import annotations
import os
from typing import Dict

class FileCache:
    def __init__(self): self._m: Dict[str, str] = {}
    def read(self, path: str) -> str:
        if path not in self._m:
            with open(path, encoding="utf-8", errors="replace") as f: self._m[path] = f.read()
        return self._m[path]
    def cached(self, path: str) -> bool: return path in self._m
    def size(self) -> int: return len(self._m)

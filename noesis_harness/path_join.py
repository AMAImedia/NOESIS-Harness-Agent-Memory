"""noesis_harness/path_join.py — safe path join (stays under base).

Patterns: LoopX safe path join.
Stdlib only.
"""
from __future__ import annotations
import os

def safe_join(base: str, *parts: str) -> str:
    base = os.path.abspath(base)
    path = os.path.abspath(os.path.join(base, *parts))
    if path != base and not path.startswith(base + os.sep): raise ValueError("escape")
    return path

"""noesis_harness/glob_util.py — filename pattern matching (glob).

Patterns: LoopX glob.
Stdlib only.
"""
from __future__ import annotations
import fnmatch

def match(pattern: str, name: str) -> bool:
    return fnmatch.fnmatch(name, pattern)
def filter(names: list, pattern: str) -> list:
    return fnmatch.filter(names, pattern)

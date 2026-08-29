"""noesis_harness/dir_util.py — directory helpers.

Patterns: LoopX dir util.
Stdlib only.
"""
from __future__ import annotations
import os

def count_files(path: str) -> int:
    return sum(1 for _ in os.scandir(path) if _.is_file())
def count_dirs(path: str) -> int:
    return sum(1 for _ in os.scandir(path) if _.is_dir())
def list_files(path: str) -> list:
    return sorted(e.name for e in os.scandir(path) if e.is_file())
def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)
def is_empty(path: str) -> bool:
    return not any(os.scandir(path))

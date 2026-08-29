"""noesis_harness/file_stat.py — file stat helpers.

Patterns: LoopX stat.
Stdlib only.
"""
from __future__ import annotations
import os, time

def file_size(path: str) -> int:
    return os.path.getsize(path)
def is_file(path: str) -> bool:
    return os.path.isfile(path)
def is_dir(path: str) -> bool:
    return os.path.isdir(path)
def mtime(path: str) -> float:
    return os.path.getmtime(path)
def age_seconds(path: str) -> float:
    return time.time() - mtime(path)

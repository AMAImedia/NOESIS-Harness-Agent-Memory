"""noesis_harness/path_util.py — path manipulation.

Patterns: LoopX path.
Stdlib only.
"""
from __future__ import annotations
import os

def stem(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]
def ext(path: str) -> str:
    return os.path.splitext(path)[1]
def join(*parts: str) -> str:
    return os.path.join(*parts)
def parent(path: str) -> str:
    return os.path.dirname(os.path.abspath(path))
def filename(path: str) -> str:
    return os.path.basename(path)

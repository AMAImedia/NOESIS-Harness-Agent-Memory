"""noesis_harness/chunked_read.py — chunked reading from iterator.

Patterns: LoopX chunked read.
Stdlib only.
"""
from __future__ import annotations
from typing import Iterator, List, Any

def chunked(iterable, size: int) -> Iterator[list]:
    if size < 1: raise ValueError("size >=1")
    chunk = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) >= size: yield chunk; chunk = []
    if chunk: yield chunk
def head(iterable, n: int) -> list:
    out = []
    for item in iterable:
        out.append(item)
        if len(out) >= n: break
    return out
def tail(iterable, n: int) -> list:
    out = []
    for item in iterable:
        out.append(item)
        if len(out) > n: out.pop(0)
    return out

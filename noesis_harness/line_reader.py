"""noesis_harness/line_reader.py — lazy line reader.

Patterns: LoopX line reader.
Stdlib only.
"""
from __future__ import annotations
from typing import Iterator, List

def read_lines(path: str) -> List[str]:
    out = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f: out.append(line.rstrip("\n"))
    return out
def iter_lines(path: str) -> Iterator[str]:
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f: yield line.rstrip("\n")

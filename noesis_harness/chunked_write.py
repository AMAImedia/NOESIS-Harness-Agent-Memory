"""noesis_harness/chunked_write.py — chunked write to file.

Patterns: LoopX chunked IO.
Stdlib only.
"""
from __future__ import annotations
from typing import Iterator

def write_chunks(path: str, chunks: Iterator[bytes], chunk_size: int = 4096) -> int:
    total = 0
    with open(path, "wb") as f:
        for chunk in chunks:
            f.write(chunk); total += len(chunk)
    return total
def write_lines(path: str, lines: Iterator[str]) -> int:
    total = 0
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n"); total += 1
    return total

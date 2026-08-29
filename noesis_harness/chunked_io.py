"""noesis_harness/chunked_io.py — chunked read/write helpers.

Patterns: LoopX chunked IO.
Stdlib only.
"""
from __future__ import annotations
from typing import Iterator

def read_chunks(path: str, size: int = 4096) -> Iterator[bytes]:
    with open(path, "rb") as f:
        while True:
            chunk = f.read(size)
            if not chunk: break
            yield chunk
def write_chunks(path: str, chunks: Iterator[bytes]) -> int:
    total = 0
    with open(path, "wb") as f:
        for chunk in chunks: f.write(chunk); total += len(chunk)
    return total

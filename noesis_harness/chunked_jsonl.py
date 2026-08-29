"""noesis_harness/chunked_jsonl.py — chunked JSONL read/write.

Patterns: LoopX JSONL.
Stdlib only.
"""
from __future__ import annotations
import json
from typing import Iterator

def read_chunks(path: str, chunk_size: int = 100) -> Iterator[list]:
    chunk = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunk.append(json.loads(line))
                if len(chunk) >= chunk_size: yield chunk; chunk = []
    if chunk: yield chunk
def write_jsonl(path: str, items: list) -> int:
    with open(path, "w", encoding="utf-8") as f:
        for item in items: f.write(json.dumps(item, sort_keys=True) + "\n")
    return len(items)
def count_jsonl(path: str) -> int:
    n = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip(): n += 1
    return n

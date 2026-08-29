"""noesis_harness/json_stream.py — JSON-lines (JSONL) reader/writer.

Patterns: LoopX stream.
Stdlib only.
"""
from __future__ import annotations
import json
from typing import Iterator

def read_jsonl(path: str) -> Iterator[dict]:
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line: yield json.loads(line)
def write_jsonl(path: str, items: list) -> int:
    with open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, sort_keys=True) + "\n")
    return len(items)
def count_jsonl(path: str) -> int:
    n = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip(): n += 1
    return n

"""noesis_harness/ring_file.py — fixed-capacity append-only ring file.

Patterns: LoopX durable ring (truncate+atomic rename).
Stdlib only.
"""
from __future__ import annotations
import json
import os
import tempfile

class RingFile:
    def __init__(self, path: str, capacity: int):
        if capacity < 1:
            raise ValueError("capacity must be >=1")
        self.path = path
        self.capacity = capacity
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)

    def append(self, line: str) -> None:
        lines = self.read_all()
        lines.append(line)
        if len(lines) > self.capacity:
            lines = lines[-self.capacity:]
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            for l in lines:
                fh.write(l + "\n")
        os.replace(tmp, self.path)

    def read_all(self):
        if not os.path.isfile(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as fh:
            return [l.rstrip("\n") for l in fh if l.strip() != ""]

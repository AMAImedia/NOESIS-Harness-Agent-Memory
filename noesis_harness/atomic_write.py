"""noesis_harness/atomic_write.py — atomic file write via temp + rename.

Patterns: LoopX atomic write.
Stdlib only.
"""
from __future__ import annotations
import os, tempfile

def atomic_write(path: str, data: bytes, tmp_dir: str = None) -> None:
    d = tmp_dir or os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d)
    try:
        with os.fdopen(fd, "wb") as f: f.write(data)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.remove(tmp)

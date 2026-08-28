"""noesis_harness/tempfile_util.py — scoped temp path helpers.

Patterns: LoopX tempfile util.
Stdlib only.
"""
from __future__ import annotations
import os, tempfile

def make_temp_dir(base: str = None) -> str:
    return tempfile.mkdtemp(dir=base)
def make_temp_file(base: str = None, suffix: str = ".tmp") -> str:
    fd, path = tempfile.mkstemp(dir=base, suffix=suffix)
    os.close(fd)
    return path

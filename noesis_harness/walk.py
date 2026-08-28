"""noesis_harness/walk.py — recursive file walk with filtering.

Patterns: LoopX walk.
Stdlib only.
"""
from __future__ import annotations
import os
from typing import List

def walk(root: str, ext: str = None) -> List[str]:
    out = []
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if ext is None or f.endswith(ext):
                out.append(os.path.join(dirpath, f))
    return sorted(out)

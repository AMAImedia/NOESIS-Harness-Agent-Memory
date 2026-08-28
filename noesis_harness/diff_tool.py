"""noesis_harness/diff_tool.py — diff two dict snapshots.

Patterns: LoopX snapshot diff.
Stdlib only.
"""
from __future__ import annotations
from typing import Dict, Any

def diff(a: Dict[str, Any], b: Dict[str, Any]):
    keys = set(a.keys()) | set(b.keys())
    added = sorted([k for k in keys if k not in a])
    removed = sorted([k for k in keys if k not in b])
    changed = sorted([k for k in keys if k in a and k in b and a[k] != b[k]])
    return {"added": added, "removed": removed, "changed": changed}

"""noesis_harness/queue_view.py — read-only view of a queue file.

Patterns: LoopX queue projection.
Stdlib only.
"""
from __future__ import annotations
import json, os

def view(path: str):
    if not os.path.isfile(path): return {"items": [], "count": 0}
    try:
        data = json.loads(open(path, encoding="utf-8").read())
        if isinstance(data, list): return {"items": data, "count": len(data)}
        return {"items": [], "count": 0}
    except (ValueError, OSError): return {"items": [], "count": 0}

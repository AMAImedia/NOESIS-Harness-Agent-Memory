"""noesis_harness/singleton.py — singleton pattern.

Patterns: LoopX singleton.
Stdlib only.
"""
from __future__ import annotations
from typing import Dict, Any

_instances: Dict[type, Any] = {}

def get_instance(cls, *args, **kwargs):
    if cls not in _instances: _instances[cls] = cls(*args, **kwargs)
    return _instances[cls]
def reset(cls) -> bool:
    return _instances.pop(cls, None) is not None
def clear_all() -> int:
    n = len(_instances); _instances.clear(); return n

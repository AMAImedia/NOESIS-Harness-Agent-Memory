"""noesis_harness/env_parse.py — typed env var parsing.

Patterns: LoopX env parse.
Stdlib only.
"""
from __future__ import annotations
import os
from typing import Any, Optional

def get_int(name: str, default: int = 0) -> int:
    v = os.environ.get(name)
    if v is None or v == "": return default
    try: return int(v)
    except ValueError: return default
def get_bool(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None: return default
    return v.strip().lower() in ("1", "true", "yes", "on")
def get_str(name: str, default: str = "") -> str:
    v = os.environ.get(name)
    return v if v is not None else default

"""noesis_harness/uuid_util.py — UUID helpers.

Patterns: LoopX UUID.
Stdlib only.
"""
from __future__ import annotations
import uuid

def new() -> str:
    return str(uuid.uuid4())
def new_short() -> str:
    return uuid.uuid4().hex[:12]
def is_valid(text: str) -> bool:
    try: uuid.UUID(text); return True
    except ValueError: return False
def from_bytes(data: bytes) -> str:
    return str(uuid.UUID(bytes=data))

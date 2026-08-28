"""noesis_harness/result.py — Result Ok/Err.

Patterns: LoopX result.
Stdlib only.
"""
from __future__ import annotations
from typing import Any

class Ok:
    def __init__(self, value: Any): self.value = value
    def is_ok(self): return True
    def is_err(self): return False
    def unwrap(self): return self.value

class Err:
    def __init__(self, error: Any): self.error = error
    def is_ok(self): return False
    def is_err(self): return True
    def unwrap(self): raise ValueError(str(self.error))

def ok(value): return Ok(value)
def err(error): return Err(error)

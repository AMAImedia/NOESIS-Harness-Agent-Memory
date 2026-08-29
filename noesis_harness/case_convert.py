"""noesis_harness/case_convert.py — snake/camel/kebab.

Patterns: LoopX case.
Stdlib only.
"""
from __future__ import annotations
import re

def to_snake(s: str) -> str:
    s=re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s); s=re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    return re.sub(r"[\-\s]+","_", s).lower().strip("_")
def to_camel(s: str) -> str:
    parts=re.split(r"[_\-\s]+", s); return parts[0].lower() + "".join(p.capitalize() for p in parts[1:] if p)
def to_kebab(s: str) -> str: return to_snake(s).replace("_","-")

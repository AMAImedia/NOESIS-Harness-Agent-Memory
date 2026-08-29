"""noesis_harness/time_format.py — time formatting.

Patterns: LoopX time format.
Stdlib only.
"""
from __future__ import annotations
import datetime

def format_time(dt: datetime.time, fmt: str = "%H:%M:%S") -> str:
    return dt.strftime(fmt)
def format_hm(dt: datetime.time) -> str:
    return dt.strftime("%H:%M")
def now_str(fmt: str = "%H:%M:%S") -> str:
    return datetime.datetime.now().strftime(fmt)

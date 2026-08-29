"""noesis_harness/time_parse.py — time string parsing.

Patterns: LoopX time parse.
Stdlib only.
"""
from __future__ import annotations
import datetime

_FMTS = ["%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M:%S %p"]

def parse_time(text: str) -> datetime.time:
    for fmt in _FMTS:
        try: return datetime.datetime.strptime(text.strip(), fmt).time()
        except ValueError: continue
    raise ValueError("no format matches")
def parse_or_default(text: str, default: datetime.time = None) -> datetime.time:
    try: return parse_time(text)
    except ValueError: return default or datetime.time(0, 0)

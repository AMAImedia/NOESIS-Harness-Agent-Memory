"""noesis_harness/date_parse.py — date string parsing.

Patterns: LoopX date parse.
Stdlib only.
"""
from __future__ import annotations
import datetime

_FMTS = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%d.%m.%Y", "%Y%m%d"]

def parse_date(text: str) -> datetime.date:
    for fmt in _FMTS:
        try: return datetime.datetime.strptime(text, fmt).date()
        except ValueError: continue
    raise ValueError("no format matches")
def parse_datetime(text: str) -> datetime.datetime:
    for fmt in _FMTS:
        try: return datetime.datetime.strptime(text, fmt)
        except ValueError: continue
    raise ValueError("no format matches")
def parse_or_default(text: str, default: datetime.date = None) -> datetime.date:
    try: return parse_date(text)
    except ValueError: return default or datetime.date.today()

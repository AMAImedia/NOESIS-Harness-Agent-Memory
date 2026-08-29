"""noesis_harness/date_format.py — date formatting.

Patterns: LoopX date format.
Stdlib only.
"""
from __future__ import annotations
import datetime

def format_date(dt: datetime.datetime, fmt: str = "%Y-%m-%d") -> str:
    return dt.strftime(fmt)
def format_iso(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S")
def today_str(fmt: str = "%Y-%m-%d") -> str:
    return datetime.date.today().strftime(fmt)

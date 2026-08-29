"""noesis_harness/timestamp.py — parse/format ISO 8601 timestamps.

Patterns: LoopX timestamp.
Stdlib only.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional

def parse_iso(text: str) -> datetime:
    text = text.strip().replace("Z", "+00:00")
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M%z"):
        try: return datetime.fromisoformat(text) if "+" in text or text.endswith("Z") else datetime.strptime(text, fmt)
        except ValueError: pass
    return datetime.fromisoformat(text)

def format_iso(dt: datetime, utc: bool = True) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc) if utc else dt
    return dt.isoformat().replace("+00:00", "Z")

def now_iso() -> str:
    return format_iso(datetime.now(timezone.utc))
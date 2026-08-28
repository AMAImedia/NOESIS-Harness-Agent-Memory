"""noesis_harness/event_filter.py — read-only event filter.

Patterns: LoopX filtered projection.
Stdlib only.
"""
from __future__ import annotations
from typing import List, Dict, Any
from noesis_harness.event_store import EventStore

def filter_by_type(events_path: str, type_name: str) -> List[Dict[str, Any]]:
    return [r for r in EventStore(events_path).iter_events() if r.get("type") == type_name]

def filter_by_payload_key(events_path: str, key: str, value: Any) -> List[Dict[str, Any]]:
    out = []
    for r in EventStore(events_path).iter_events():
        payload = r.get("payload")
        if isinstance(payload, dict) and payload.get(key) == value:
            out.append(r)
    return out

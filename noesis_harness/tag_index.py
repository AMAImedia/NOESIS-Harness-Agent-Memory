"""noesis_harness/tag_index.py — read-only tag index over event log.

Patterns: agentmemory/LoopX inverted index.
Stdlib only.
"""
from __future__ import annotations
import json, re
from noesis_harness.event_store import EventStore

_TAG = re.compile(r"#(\w+)")

def build(events_path: str):
    idx = {}
    for rec in EventStore(events_path).iter_events():
        text = json.dumps(rec.get("payload", rec), ensure_ascii=False, default=str)
        for tag in set(_TAG.findall(text)):
            idx.setdefault(tag.lower(), []).append(rec.get("event_id", ""))
    return idx

def search(index: dict, tag: str):
    return list(index.get(tag.lower().lstrip("#"), []))

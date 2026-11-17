"""noesis_harness/projection_cache.py

Read-only, deterministic projection cache over the append-only event log.

Patterns adapted from:
  - LoopX (state_projection.py: build_state_projection folds events into a
    compact snapshot so the full log need not be replayed on every read)
  - deepseek-harness (replay.py: replay is a pure function over the event
    stream; the snapshot is a stable digest of that replay)

The snapshot never mutates the log. It is a pure function of the event stream:
the same log always yields the same snapshot and the same sha256 digest. This
makes it safe to cache and to detect log tampering (a drifted digest means the
log changed).

Zero dependencies (stdlib only). One file, one job.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, Iterable, Optional

from noesis_harness.event_store import EventStore

SNAPSHOT_VERSION = "1"


def _event_key(event: Dict[str, Any]) -> Optional[str]:
    """Resolve the optional `key` that groups an event for by_key projection.

    A key may live at the record level or inside a dict payload. Records without
    a key are simply not represented in `by_key`.
    """
    key = event.get("key")
    if key is None:
        payload = event.get("payload")
        if isinstance(payload, dict):
            key = payload.get("key")
    if key is None:
        return None
    return str(key)


def _canonical(snapshot: Dict[str, Any]) -> str:
    """Deterministic JSON serialization of a snapshot (digest excluded)."""
    return json.dumps(
        snapshot,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )


def _digest(snapshot: Dict[str, Any]) -> str:
    """sha256 over the canonical snapshot, prefixed for readability."""
    return "sha256:" + hashlib.sha256(
        _canonical(snapshot).encode("utf-8")
    ).hexdigest()


def project(store_path: str) -> Dict[str, Any]:
    """Build a read-only, deterministic snapshot of an append-only event log.

    Reads events via EventStore(path).iter_events(). Never writes. Returns a
    JSON-serializable dict with:
      - record_count: number of events replayed
      - last_seq: highest seq seen (None if the log is empty)
      - last_event_id: event_id of the final event (None if empty)
      - types: count of events per `type`
      - by_key: latest payload per `key` field (last write wins by append order)
      - digest: sha256 over the canonical snapshot (prefix "sha256:")

    Pure function of the log: identical input -> identical output + digest.
    """
    store = EventStore(store_path)
    record_count = 0
    last_seq: Optional[int] = None
    last_event_id: Optional[str] = None
    types: Dict[str, int] = {}
    by_key: Dict[str, Any] = {}

    events: Iterable[Dict[str, Any]] = store.iter_events()
    for event in events:
        record_count += 1
        seq = event.get("seq")
        if isinstance(seq, int):
            last_seq = seq
        event_id = event.get("event_id")
        if event_id is not None:
            last_event_id = str(event_id)
        event_type = event.get("type")
        if event_type is not None:
            key = str(event_type)
            types[key] = types.get(key, 0) + 1
        resolved = _event_key(event)
        if resolved is not None:
            by_key[resolved] = event.get("payload")

    snapshot: Dict[str, Any] = {
        "version": SNAPSHOT_VERSION,
        "record_count": record_count,
        "last_seq": last_seq,
        "last_event_id": last_event_id,
        "types": dict(sorted(types.items())),
        "by_key": dict(sorted(by_key.items())),
    }
    snapshot["digest"] = _digest(snapshot)
    return snapshot


def snapshot_file(path: str) -> Dict[str, Any]:
    """Load a previously written snapshot JSON file (used by tests/tooling)."""
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_snapshot(store_path: str, out_path: str) -> Dict[str, Any]:
    """Convenience: build a snapshot and persist it as JSON.

    Read-only with respect to the event log; only the snapshot file is written.
    """
    snapshot = project(store_path)
    directory = os.path.dirname(os.path.abspath(out_path))
    os.makedirs(directory, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, sort_keys=True, ensure_ascii=False, indent=2)
    return snapshot


__all__ = ["project", "snapshot_file", "write_snapshot", "SNAPSHOT_VERSION"]

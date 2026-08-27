"""noesis_harness/lease_metrics.py

Read-only lease metrics projection for the local-first Agent OS.

Patterns adapted from:
  - agentmemory (leases.ts: TTL + one-holder invariants)
  - LoopX (state_projection integrity / replay-determinism checks)
  - Hermes (operator snapshot read-only projection discipline)

This module derives a small, stable metrics dict from the SQLite lease /
coordination store that `noesis_harness.self_audit.audit_coordination` audits.
It is strictly read-only: it never opens the store for writing and never
appends events. Determinism is preserved by reusing the same `now` default
semantics as `audit_coordination` (when `now` is None the latest `acquired_at`
in the data is used), so identical inputs always yield identical metrics.

Zero dependencies (stdlib only: sqlite3, time).
"""

from __future__ import annotations

import os
import sqlite3
from typing import Dict, Optional

from noesis_harness.self_audit import audit_coordination


def metrics(db_path, now=None):
    # type: (str, Optional[float]) -> Dict[str, object]
    """Read-only lease metrics derived from the coordination store.

    Returns a dict with:
      - present (bool): True if the db and leases table exist and are readable.
      - total (int): total number of lease rows.
      - active (int): number of rows with status == "active".
      - expired (int): number of active rows whose expires_at <= now.
      - per_holder (dict): holder -> count of active leases it owns.

    Missing db or missing leases table yields present=False and zeroed counts
    (fail-closed, like audit_coordination). The store is opened read-only via a
    URI so no write lock or mutation can occur.
    """
    out = {
        "present": False,
        "total": 0,
        "active": 0,
        "expired": 0,
        "per_holder": {},
    }  # type: Dict[str, object]

    if not os.path.exists(db_path):
        return out

    try:
        uri = "file:%s?mode=ro" % db_path.replace("\\", "/")
        conn = sqlite3.connect(uri, timeout=10, uri=True)
        conn.row_factory = sqlite3.Row
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        if "leases" not in tables:
            conn.close()
            return out
        rows = [dict(r) for r in conn.execute(
            "SELECT task_key, holder, acquired_at, expires_at, status FROM leases")]
        conn.close()
    except sqlite3.Error:
        return out

    if now is None:
        now = max((float(r.get("acquired_at") or 0) for r in rows), default=0.0)

    total = 0
    active = 0
    expired = 0
    per_holder = {}  # type: Dict[str, int]

    for r in rows:
        total += 1
        if str(r.get("status", "")) != "active":
            continue
        active += 1
        holder = str(r.get("holder", ""))
        per_holder[holder] = per_holder.get(holder, 0) + 1
        expires_at = r.get("expires_at")
        if isinstance(expires_at, (int, float)) and float(expires_at) <= now:
            expired += 1

    out["present"] = True
    out["total"] = total
    out["active"] = active
    out["expired"] = expired
    out["per_holder"] = per_holder
    return out


def read_only_contract(db_path, now=None):
    # type: (str, Optional[float]) -> bool
    """Convenience predicate: True iff the store can be read without error.

    Mirrors the fail-closed contract of audit_coordination; useful for tests
    that assert the metrics path never raises on a missing/unreadable store.
    """
    try:
        metrics(db_path, now=now)
        return True
    except Exception:
        return False

"""noesis_harness/ttl_watch.py

Read-only TTL watch over the SQLite lease / coordination store.

Patterns adapted from:
  - agentmemory (leases.ts: TTL windowing + one-holder invariants)
  - Hermes (operator snapshot read-only projection discipline)
  - LoopX (deterministic, replay-stable projection reads)

This module is a thin, side-effect-free observer. It NEVER writes to the
lease store. It reuses noesis_harness.self_audit.audit_coordination to fold in
the control-plane integrity findings (missing store, missing table, expired
active leases, holder overlap) and layers a TTL windowing projection on top so
an operator can see, at a glance:

  - which leases are currently active,
  - which active leases are already past their TTL (expired_active),
  - which active leases will expire inside a configurable look-ahead window
    (soon_to_expire), and
  - whether the coordinated state looks healthy overall (ok).

Determinism: given the same db_path and `now`, `watch` returns byte-for-byte
the same structure. A `threading.Lock` is deliberately NOT used: SQLite opened
in read-only mode with a short timeout is safe for concurrent readers, and the
watch must not gate or serialize other processes.

Zero dependencies (stdlib only).
"""

from __future__ import annotations

import os
import sqlite3
import time
from typing import Any, Dict, List, Optional

from noesis_harness.self_audit import audit_coordination


DEFAULT_WINDOW_SECONDS = 300.0


def _read_leases(db_path):
    # type: (str) -> List[Dict[str, Any]]
    """Read-only snapshot of the leases table (Lock-free)."""
    if not os.path.exists(db_path):
        return []
    conn = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True, timeout=10)
    try:
        conn.row_factory = sqlite3.Row
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        if "leases" not in tables:
            return []
        rows = [dict(r) for r in conn.execute(
            "SELECT task_key, holder, acquired_at, expires_at, status FROM leases")]
    except sqlite3.Error:
        return []
    finally:
        conn.close()
    return rows


def watch(db_path, now=None, window=DEFAULT_WINDOW_SECONDS):
    # type: (str, Optional[float], float) -> Dict[str, Any]
    """Read-only TTL projection of the lease store.

    Args:
      db_path: path to the SQLite coordination store.
      now: reference time in epoch seconds. Defaults to time.time().
      window: look-ahead window in seconds for soon_to_expire (default 300).

    Returns a dict with:
      active: list of active lease rows (task_key, holder, acquired_at,
              expires_at, status),
      expired_active: {"holders": [...], "count": int} for active leases whose
              expires_at <= now,
      soon_to_expire: list of active leases whose now < expires_at <= now+window,
      ok: bool — True when there are no expired active leases AND the
              coordination self-audit reports no error/critical findings,
      present: bool — True when the store and leases table were readable,
      now: the reference time used,
      window: the look-ahead window used.
    """
    if now is None:
        now = time.time()

    rows = _read_leases(db_path)
    present = len(rows) > 0 or os.path.exists(db_path)

    active = []  # type: List[Dict[str, Any]]
    expired_holders = []  # type: List[str]
    expired_count = 0
    soon = []  # type: List[Dict[str, Any]]

    for r in rows:
        if str(r.get("status", "")) != "active":
            continue
        active.append(r)
        expires_at = r.get("expires_at")
        if not isinstance(expires_at, (int, float)):
            continue
        exp = float(expires_at)
        if exp <= now:
            expired_count += 1
            holder = str(r.get("holder", ""))
            if holder not in expired_holders:
                expired_holders.append(holder)
        elif exp <= now + window:
            soon.append(r)

    audit = audit_coordination(db_path, now=now)
    expired_in_audit = any(
        f.get("code") == "lease_expired_active" for f in audit.findings)
    ok = (not expired_in_audit) and (expired_count == 0) and audit.ok

    return {
        "active": active,
        "expired_active": {"holders": expired_holders, "count": expired_count},
        "soon_to_expire": soon,
        "ok": ok,
        "present": present,
        "now": now,
        "window": window,
    }

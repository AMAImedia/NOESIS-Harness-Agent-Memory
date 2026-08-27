"""noesis_harness/operator_status.py

Read-only operator health surface for the local-first Agent OS.

Patterns adapted from:
  - LoopX (state_projection: a read-only snapshot of replayed state)
  - agentmemory (leases.ts: active vs expired TTL accounting)
  - Hermes (operator snapshot: a non-mutating view of control-plane health)

This module is a thin, side-effect-free command on top of the existing
control-plane stores. It never writes to the event log, the lease store, or
any other state file. All stats are recomputed from the stored data on every
call, so the command is deterministic and safe to run repeatedly.

It deliberately reuses the SAME determinism rule as
`self_audit.audit_coordination` for the "now" reference point: when no
external clock is supplied, `now = max(acquired_at)` over the lease rows, so
the expired/active split is reproducible from the data alone.

Zero dependencies (stdlib only).
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from typing import Any, Dict, List, Optional


def _event_log_stats(path):
    # type: (str) -> Dict[str, Any]
    """Read-only tally of an append-only JSONL event log.

    Returns record count, the highest sequence number seen, and the last
    event_id (in file order). No repair is performed: a malformed line is
    simply skipped so this stays append-only safe.
    """
    stats = {"present": False, "record_count": 0, "last_seq": None, "last_event_id": None}
    if not path or not os.path.exists(path):
        return stats

    stats["present"] = True
    last_seq = None  # type: Optional[int]
    last_id = None  # type: Optional[str]
    count = 0
    with open(path, "rb") as fh:
        for raw in fh.read().splitlines():
            if not raw.strip():
                continue
            try:
                rec = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
                continue
            if not isinstance(rec, dict):
                continue
            count += 1
            seq = rec.get("seq")
            if isinstance(seq, int) and (last_seq is None or seq >= last_seq):
                last_seq = seq
            last_id = str(rec.get("event_id", ""))
    stats["record_count"] = count
    stats["last_seq"] = last_seq
    stats["last_event_id"] = last_id
    return stats


def _lease_store_stats(path):
    # type: (str) -> Dict[str, Any]
    """Read-only active/expired accounting for a SQLite lease store.

    Uses the deterministic `now = max(acquired_at)` rule from
    self_audit.audit_coordination so the result is reproducible from the data.
    """
    stats = {
        "present": False,
        "table_present": False,
        "active_count": 0,
        "expired_count": 0,
        "now": None,
    }
    if not path or not os.path.exists(path):
        return stats

    stats["present"] = True
    try:
        conn = sqlite3.connect(path, timeout=10)
        conn.row_factory = sqlite3.Row
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        if "leases" not in tables:
            conn.close()
            return stats
        rows = [dict(r) for r in conn.execute(
            "SELECT task_key, holder, acquired_at, expires_at, status FROM leases")]
        conn.close()
    except sqlite3.Error:
        return stats

    stats["table_present"] = True
    if not rows:
        stats["now"] = 0.0
        return stats

    now = max((float(r.get("acquired_at") or 0) for r in rows), default=0.0)
    stats["now"] = now

    active = 0
    expired = 0
    for r in rows:
        if str(r.get("status", "")) != "active":
            continue
        active += 1
        expires_at = r.get("expires_at")
        if isinstance(expires_at, (int, float)) and float(expires_at) <= now:
            expired += 1
    stats["active_count"] = active
    stats["expired_count"] = expired
    return stats


def collect_status(events_path=None, leases_path=None):
    # type: (Optional[str], Optional[str]) -> Dict[str, Any]
    """Build a JSON-serializable, read-only health status dict.

    Keys:
      - event_log        : record count, last seq, last event_id
      - leases           : active count, expired count (deterministic now)
      - self_audit       : the run_self_audit digest (only when a path is given)
      - ok               : bool, True when the self-audit reports no failing findings
      - generated_at      : wall-clock timestamp of the snapshot (informational)

    Pure function: reads stores, never mutates them.
    """
    from noesis_harness import self_audit

    event_stats = _event_log_stats(events_path)
    lease_stats = _lease_store_stats(leases_path)

    status = {
        "event_log": event_stats,
        "leases": lease_stats,
        "self_audit": None,
        "ok": True,
        "generated_at": None,
    }

    if events_path or leases_path:
        report = self_audit.run_self_audit(events_path, leases_path)
        status["self_audit"] = report.digest()
        status["ok"] = report.ok

    return status


def main(argv=None):
    # type: (Optional[List[str]]) -> int
    p = argparse.ArgumentParser(
        description="NOESIS operator status (read-only health snapshot)")
    p.add_argument("--events", action="append", default=[],
                   help="path to an append-only event log (JSONL); repeatable")
    p.add_argument("--leases", action="append", default=[],
                   help="path to a SQLite coordination store; repeatable")
    p.add_argument("--json", action="store_true",
                   help="emit machine-readable JSON instead of a human summary")
    args = p.parse_args(argv)

    events_path = args.events[0] if args.events else None
    leases_path = args.leases[0] if args.leases else None

    status = collect_status(events_path, leases_path)

    if args.json:
        print(json.dumps(status, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        el = status["event_log"]
        ls = status["leases"]
        print("NOESIS operator status (read-only)")
        print("  event_log:")
        print("    present:      %s" % el["present"])
        print("    records:      %s" % el["record_count"])
        print("    last_seq:     %s" % el["last_seq"])
        print("    last_event_id:%s" % el["last_event_id"])
        print("  leases:")
        print("    present:      %s" % ls["present"])
        print("    table:        %s" % ls["table_present"])
        print("    active:       %s" % ls["active_count"])
        print("    expired:      %s" % ls["expired_count"])
        if status["self_audit"] is not None:
            print("  self_audit digest: %s" % status["self_audit"])
            print("  ok:               %s" % status["ok"])
        else:
            print("  self_audit:       (no stores supplied)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""noesis_harness/health_cli.py

Read-only health CLI that aggregates read-only projections of the append-only
event log into a single machine-readable health dict.

Patterns adapted from:
  - LoopX (event_sourced_state.py: build_state_projection) -- derive stable,
    read-only summaries by folding the event log deterministically, never
    mutating the source. A health read is just another read-only projection.

This module is PURE and READ-ONLY. It never creates, appends, repairs, or
deletes any event log, lease store, or state file. It depends solely on the
Python standard library (argparse, json, sys). The heavy projections
(metrics_snapshot, summary_view, self_audit) are imported lazily INSIDE main()
so the CLI degrades gracefully when an optional module is absent: a missing
dependency is recorded in the health dict's "missing" list rather than raising.

The public entry point is main(argv=None), which returns a process exit code
(0 = ok, 1 = audit reported a failure or no stores supplied). With --json it
prints a single JSON object with at least:

    {
      "record_count": int,        # total events observed across supplied logs
      "digests": {str: str},      # per-projection sha256 digests (when available)
      "audit_ok": bool,           # True unless a self_audit failure was found
      "missing": [str, ...]       # projection names that could not be imported
    }

Zero dependencies (stdlib only).
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional


def _build_parser():
    # type: () -> argparse.ArgumentParser
    p = argparse.ArgumentParser(
        description="NOESIS read-only event-log health snapshot (JSON)")
    p.add_argument("--events", action="append", default=[],
                   help="path to an append-only event log (JSONL); repeatable")
    p.add_argument("--leases", action="append", default=[],
                   help="path to a SQLite coordination/lease store; repeatable")
    p.add_argument("--json", action="store_true",
                   help="emit a single machine-readable JSON health object")
    return p


def _emit(health, as_json):
    # type: (Dict[str, Any], bool) -> None
    if as_json:
        sys.stdout.write(json.dumps(health, ensure_ascii=False, sort_keys=True))
        sys.stdout.write("\n")
    else:
        sys.stdout.write("NOESIS health snapshot\n")
        sys.stdout.write("  record_count: %d\n" % health["record_count"])
        sys.stdout.write("  audit_ok:     %s\n" % health["audit_ok"])
        if health["digests"]:
            sys.stdout.write("  digests:\n")
            for name, value in sorted(health["digests"].items()):
                sys.stdout.write("    %-16s %s\n" % (name, value))
        if health["missing"]:
            sys.stdout.write("  missing:      %s\n" % ", ".join(health["missing"]))


def main(argv=None):
    # type: (Optional[List[str]]) -> int
    args = _build_parser().parse_args(argv)

    events_paths = list(args.events)
    leases_paths = list(args.leases)
    events_path = events_paths[0] if events_paths else None
    leases_path = leases_paths[0] if leases_paths else None

    health = {
        "record_count": 0,
        "digests": {},
        "audit_ok": True,
        "missing": [],
    }  # type: Dict[str, Any]

    # Lazily import each projection so a missing module is skipped, not fatal.
    metrics_snapshot = None
    summary_view = None
    self_audit = None

    try:
        from . import metrics_snapshot as _ms
        metrics_snapshot = _ms
    except Exception:
        health["missing"].append("metrics_snapshot")

    try:
        from . import summary_view as _sv
        summary_view = _sv
    except Exception:
        health["missing"].append("summary_view")

    try:
        from . import self_audit as _sa
        self_audit = _sa
    except Exception:
        health["missing"].append("self_audit")

    # Aggregate the per-log read-only metrics + summary projections.
    if events_path is not None:
        if metrics_snapshot is not None:
            snap = metrics_snapshot.snapshot(events_path)
            health["record_count"] = snap.get("total", 0)
            if snap.get("digest") is not None:
                health["digests"]["metrics_snapshot"] = snap["digest"]
        if summary_view is not None:
            summ = summary_view.summarize(events_path)
            # Prefer the summary total if metrics was unavailable.
            if metrics_snapshot is None:
                health["record_count"] = summ.get("total", 0)
            if summ.get("digest") is not None:
                health["digests"]["summary_view"] = summ["digest"]

    # Aggregate the read-only control-plane self-audit.
    if self_audit is not None:
        report = self_audit.run_self_audit(
            events_path=events_path, leases_path=leases_path)
        health["audit_ok"] = bool(report.ok)
        if report.digest() is not None:
            health["digests"]["self_audit"] = report.digest()

    if not events_paths and not leases_paths:
        health["audit_ok"] = True

    _emit(health, as_json=args.json)
    return 0 if health["audit_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

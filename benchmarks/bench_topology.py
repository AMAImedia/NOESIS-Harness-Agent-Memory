"""Micro-benchmark for noesis_harness.event_topology.

Patterns borrowed from:
- LoopX (event_sourced_state.py): a pure, read-only projection over an
  append-only event log. event_topology never mutates the source log; build()
  returns a derived dependency graph that is a deterministic replay projection.
  This benchmark generates a synthetic acyclic event log with parent /
  depends_on links and confirms the derived graph is cycle-free, the exact
  invariant LoopX relies on for stable replay.

This module is stdlib-only and writes nothing outside the system TEMP
directory. event_topology is imported lazily so the benchmark can be collected
by the test runner even if the package import path is not yet on sys.path.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def _make_events(n):
    """Build ``n`` synthetic event records with acyclic dependency links.

    Each event ``i`` depends on a prior event, forming a forest of chains.
    Because every edge points backward to a lower index, the resulting graph is
    guaranteed acyclic (cycle_free == True).
    """
    events = []
    for i in range(n):
        parent = max(i - 1, 0) if i > 0 else None
        depends_on = []
        if i >= 2:
            depends_on.append(max(i - 2, 0))
        payload = {}
        if parent is not None:
            payload["parent"] = "evt-%d" % parent
        if depends_on:
            payload["depends_on"] = ["evt-%d" % d for d in depends_on]
        events.append(
            {
                "event_id": "evt-%d" % i,
                "payload": payload,
            }
        )
    return events


def bench(events):
    """Write ``events`` synthetic records to TEMP and time build().

    Imports event_topology lazily. Returns a result dict with event count,
    build seconds, and passed (cycle_free must be True for the acyclic input).
    All intermediate state lives in TEMP.
    """
    import noesis_harness.event_topology as et

    scratch = tempfile.mkdtemp(prefix="noesis_bench_topology_")
    log_path = os.path.join(scratch, "events.jsonl")
    with open(log_path, "w", encoding="utf-8") as fh:
        for rec in _make_events(events):
            fh.write(json.dumps(rec))
            fh.write("\n")

    start = time.perf_counter()
    result = et.build(log_path)
    seconds = time.perf_counter() - start

    return {
        "events": events,
        "seconds": seconds,
        "passed": bool(result["cycle_free"]),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Micro-benchmark event_topology.")
    parser.add_argument("--events", type=int, default=500, help="number of events")
    args = parser.parse_args(argv)

    result = bench(args.events)
    print(json.dumps(result))

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

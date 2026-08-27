"""benchmarks/bench_eventstore.py

Stdlib-only benchmark for noesis_harness.event_store append + replay.

Patterns adapted from:
  - LoopX (event_sourced_state.py: EventStore append-only log + deterministic replay)

Builds N events through EventStore, times the append and replay phases, asserts
idempotent replay (replay count == N), and prints a JSON summary.

Zero dependencies (stdlib only). Writes only to a temp directory.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _build_store(path, n):
    """Append n events and return the append duration in seconds."""
    from noesis_harness.event_store import EventStore

    store = EventStore(path)
    t0 = time.perf_counter()
    for i in range(n):
        store.append("fact", {"i": i, "v": "x%d" % i}, event_id="evt_%d" % i)
    append_sec = time.perf_counter() - t0
    return store, append_sec


def bench(events):
    """Run the append+replay benchmark on a temp file.

    Returns a dict with keys: events, append_sec, replay_sec, passed.
    """
    if events <= 0:
        raise ValueError("events must be positive")
    tmp = tempfile.mkdtemp(prefix="noesis_bench_eventstore_")
    log_path = os.path.join(tmp, "events.jsonl")

    _, append_sec = _build_store(log_path, events)

    from noesis_harness.event_store import EventStore

    t0 = time.perf_counter()
    replay_count = len(list(EventStore(log_path).iter_events()))
    replay_sec = time.perf_counter() - t0

    passed = replay_count == events

    return {
        "events": events,
        "append_sec": append_sec,
        "replay_sec": replay_sec,
        "passed": passed,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Benchmark noesis_harness.event_store append + replay."
    )
    parser.add_argument("--events", type=int, default=1000, help="number of events")
    args = parser.parse_args(argv)

    result = bench(args.events)
    print(json.dumps(result))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())

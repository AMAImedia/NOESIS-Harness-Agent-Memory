"""Micro-benchmark for noesis_harness.projection_cache.project.

Patterns borrowed from:
- LoopX: state_projection.py folds an append-only event log into a compact,
  deterministic snapshot (build_state_projection) so the full log need not be
  replayed on every read. This benchmark replays a synthetic event log through
  that same projection path and asserts the snapshot digest is stable across two
  independent runs, which is the LoopX invariant that makes the snapshot safe to
  cache and to use as a log-integrity check.

This module is stdlib-only and writes nothing outside the system TEMP directory.
projection_cache is imported lazily so the benchmark can be collected by the test
runner even if the package import path is not yet set up.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def _build_event_log(events, path):
    """Append ``events`` synthetic records to a fresh EventStore at ``path``.

    The log mixes typed events and keyed payloads so the projection's type
    histogram and by_key latest-value maps both get exercised.
    """
    import noesis_harness.event_store as es

    store = es.EventStore(path)
    for i in range(events):
        if i % 4 == 3:
            store.append(
                "config",
                {"key": "setting-%d" % (i % 5), "value": i},
                event_id="evt-%d" % i,
            )
        else:
            store.append(
                "observation",
                {"agent": "agent-%d" % (i % 7), "index": i, "score": i * 2},
                event_id="evt-%d" % i,
            )
    return store


def bench(events):
    """Replay ``events`` synthetic records and verify projection stability.

    Builds an append-only log via EventStore, runs project() twice, and asserts
    the sha256 digest is identical across both runs. Returns a result dict with
    events, seconds, digest_stable, and passed. All state lives in TEMP.
    """
    import noesis_harness.projection_cache as pc

    scratch = tempfile.mkdtemp(prefix="noesis_bench_projection_")
    log_path = os.path.join(scratch, "events.jsonl")

    _build_event_log(events, log_path)

    start = time.perf_counter()
    first = pc.project(log_path)
    second = pc.project(log_path)
    seconds = time.perf_counter() - start

    digest_stable = first.get("digest") is not None and (
        first.get("digest") == second.get("digest")
    )
    passed = digest_stable and first.get("record_count") == events

    return {
        "events": events,
        "seconds": seconds,
        "digest_stable": digest_stable,
        "passed": passed,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Micro-benchmark projection_cache.project.")
    parser.add_argument("--events", type=int, default=500, help="number of events")
    args = parser.parse_args(argv)

    result = bench(args.events)
    print(json.dumps(result))

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

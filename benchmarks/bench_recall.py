"""benchmarks/bench_recall.py

Stdlib-only benchmark for noesis_harness.recall_augment over a synthetic
append-only event log.

Patterns adapted from:
  - LoopX       (append-only event log + deterministic replay projection)
  - agentmemory (deterministic term-overlap retrieval, no embeddings / no LLM)

This module builds N events through EventStore, ranks them with
recall_augment.rank_events for a known query, and asserts the most relevant
event lands at rank 1. It prints a single JSON line:

    {"events": N, "seconds": <float>, "top1_hit": <bool>, "passed": <bool>}

Design guarantees (see AGENTS.md):
  - Stdlib only: argparse, json, os, sys, tempfile, time.
  - recency/recall_augment is imported LAZILY inside main() so this module has
    no hard dependency on noesis_harness until it is actually run.
  - Writes only to the system TEMP directory (via tempfile.mkdtemp).
  - Deterministic, idempotent, no LLM, no network, no credentials.

Python 3.9+ syntax only: no `X | None`, no `match`.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time

# Make the repo importable whether run as a script or imported by tests.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Query tokens deliberately disjoint from the random vocabulary below so that
# only the injected "ground truth" event can achieve full term-overlap.
QUERY = "incident rollback blue service production"
GROUND_TRUTH_ID = "gt_event_0001"
GROUND_TRUTH_PAYLOAD = {
    "summary": "incident rollback blue service production resolved by oncall",
    "tags": ["incident", "rollback", "blue", "service", "production"],
}
_RANDOM_VOCAB = [
    "alpha", "beta", "gamma", "delta", "epsilon",
    "theta", "lambda", "kappa", "sigma", "omega",
]


def build_synthetic_log(store_path: str, n_events: int) -> str:
    """Build a synthetic append-only event log of N events via EventStore.

    Exactly one event (the last appended) is the ground-truth event that fully
    matches QUERY; the rest are noise from _RANDOM_VOCAB. Returns store_path.
    """
    from noesis_harness.event_store import EventStore

    store = EventStore(store_path)
    noise = n_events - 1
    for i in range(noise):
        words = _RANDOM_VOCAB[i % len(_RANDOM_VOCAB)]
        payload = {
            "summary": "noise event {0} {1}".format(i, words),
            "tags": [words],
        }
        store.append("noise", payload)
    # Ground-truth event is appended last -> highest seq -> strongest recency.
    store.append("incident", GROUND_TRUTH_PAYLOAD, event_id=GROUND_TRUTH_ID)
    return store_path


def run_benchmark(events_path: str, query: str, top_k: int):
    """Rank events for `query` and return (top1_hit, ranked, seconds)."""
    from noesis_harness import recall_augment

    start = time.time()
    ranked = recall_augment.rank_events(query, events_path, top_k=top_k)
    seconds = time.time() - start

    top1_hit = False
    if ranked:
        top1_hit = ranked[0].get("event_id") == GROUND_TRUTH_ID
    return top1_hit, ranked, seconds


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark noesis_harness.recall_augment over a synthetic log."
    )
    parser.add_argument("--events", type=int, default=200,
                        help="number of synthetic events to build (default 200)")
    parser.add_argument("--top-k", type=int, default=5, dest="top_k",
                        help="rank_events top_k (default 5)")
    args = parser.parse_args(argv)

    tmp = tempfile.mkdtemp(prefix="noesis_bench_recall_")
    store_path = os.path.join(tmp, "events.jsonl")

    build_synthetic_log(store_path, args.events)
    top1_hit, _ranked, seconds = run_benchmark(store_path, QUERY, args.top_k)

    passed = top1_hit
    result = {
        "events": args.events,
        "seconds": seconds,
        "top1_hit": top1_hit,
        "passed": passed,
    }
    print(json.dumps(result))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

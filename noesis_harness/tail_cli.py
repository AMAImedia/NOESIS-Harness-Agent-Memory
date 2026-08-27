"""noesis_harness/tail_cli.py

Read-only CLI that prints the last N events of the append-only event log.

Patterns adapted from:
  - LoopX  (event_sourced_state.py: AppendOnlyStateEventStore + iter_events)

The CLI is strictly read-only: it never appends or mutates the event log. It
opens an EventStore purely to stream events via iter_events(), keeps only the
last N events (by append/seq order), and prints one JSON object per event to
stdout. Output is deterministic: the trailing window is a stable slice of the
log, independent of how many times it is run.

Zero dependencies (stdlib only). Python 3.9+ compatible.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from typing import List, Optional

from noesis_harness import event_store


def _format_record(record: dict) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True, default=str)


def _tail(store: event_store.EventStore, n: int) -> List[dict]:
    """Return the last ``n`` events in append order (deterministic slice).

    A bounded deque keeps at most ``n`` records while streaming, so the result
    is exactly the trailing window of the log regardless of total size.
    """
    window: "deque" = deque(maxlen=n)
    for record in store.iter_events():
        window.append(record)
    return list(window)


def main(argv: Optional[List[str]] = None) -> int:
    """Print the last N events of an event log as JSON. Returns 0 on success.

    Read-only: the event log is never written to or mutated.
    """
    parser = argparse.ArgumentParser(
        prog="tail_cli",
        description="Print the last N events of the NOESIS event log (read-only).",
    )
    parser.add_argument(
        "--events",
        required=True,
        help="Path to the event log file (.jsonl) to read.",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=10,
        help="Number of trailing events to print (default: 10).",
    )
    parser.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Wrap output as a single JSON array instead of JSON lines.",
    )
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if args.n < 0:
        parser.error("--n must be non-negative")

    store = event_store.EventStore(args.events)
    window = _tail(store, args.n)

    if args.as_json:
        sys.stdout.write(
            json.dumps(window, ensure_ascii=False, sort_keys=True, default=str) + "\n"
        )
    else:
        for record in window:
            sys.stdout.write(_format_record(record) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

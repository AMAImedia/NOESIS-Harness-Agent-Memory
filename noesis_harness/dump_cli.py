"""noesis_harness/dump_cli.py

Read-only CLI that dumps the append-only event log as JSON lines.

Patterns adapted from:
  - LoopX  (event_sourced_state.py: AppendOnlyStateEventStore + iter_events)

The CLI is strictly read-only: it never appends or mutates the event log. It
opens an EventStore purely to stream events via iter_events() and prints one
compact JSON object per line (JSON Lines), optionally filtered by event type
and/or truncated to a limit, either to stdout or to a file via --out.

Zero dependencies (stdlib only). Python 3.9+ compatible.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

from noesis_harness import event_store


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dump_cli",
        description="Dump the NOESIS event log as JSON lines (read-only).",
    )
    parser.add_argument(
        "--events",
        required=True,
        help="Path to the event log file (.jsonl) to read.",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Optional path to write JSON-lines output instead of stdout.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of events to emit (most recent last).",
    )
    parser.add_argument(
        "--type",
        default=None,
        dest="event_type",
        help="Only emit events whose 'type' matches this value.",
    )
    return parser


def _format_record(record: dict) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True, default=str)


def main(argv: Optional[List[str]] = None) -> int:
    """Dump the event log as JSON lines. Returns 0 on success.

    Read-only: the event log is never written to or mutated.
    """
    parser = _build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    store = event_store.EventStore(args.events)
    emitted = 0
    sink = (
        open(args.out, "w", encoding="utf-8")
        if args.out is not None
        else sys.stdout
    )
    try:
        for record in store.iter_events():
            if (
                args.event_type is not None
                and str(record.get("type")) != args.event_type
            ):
                continue
            sink.write(_format_record(record) + "\n")
            emitted += 1
            if args.limit is not None and emitted >= args.limit:
                break
    finally:
        if sink is not sys.stdout:
            sink.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

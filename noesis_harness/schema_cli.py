"""noesis_harness/schema_cli.py

Read-only CLI that prints the event-type inventory and payload field keys of
an append-only event log.

Patterns adapted from:
  - LoopX  (event_sourced_state.py: projection over an append-only log;
            read-side introspection of type/field shape)

Design goals:
  - Strictly read-only: opens the log through EventStore.iter_events and never
    appends, mutates, or repairs any event.
  - The inventory is a pure projection: {event_type: [field_key, ...]}.
  - Zero dependencies (stdlib only). Deterministic, LLM-free, no network.

Usage:
  python -m noesis_harness.schema_cli --events PATH [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, Iterable, List

from .event_store import EventStore


def build_inventory(events: Iterable[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Project an event stream into {type: sorted field keys}.

    Field keys are the top-level keys of each event's ``payload``. The output
    is deterministic: keys are sorted and only the union of keys seen for a
    given type is reported.
    """
    inventory: Dict[str, List[str]] = {}
    for event in events:
        if not isinstance(event, dict):
            continue
        event_type = event.get("type")
        if event_type is None:
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            keys: List[str] = []
        else:
            keys = [str(k) for k in payload.keys()]
        existing = inventory.setdefault(str(event_type), [])
        for key in keys:
            if key not in existing:
                existing.append(key)
    for keys in inventory.values():
        keys.sort()
    return inventory


def _format_text(inventory: Dict[str, List[str]]) -> str:
    if not inventory:
        return "no events"
    lines: List[str] = []
    for event_type in sorted(inventory.keys()):
        keys = inventory[event_type]
        lines.append("{}: {}".format(event_type, ", ".join(keys) if keys else "(no payload fields)"))
    return "\n".join(lines)


def main(argv: Any = None) -> int:
    """Entry point. Returns a process exit code (0 on success)."""
    parser = argparse.ArgumentParser(
        prog="schema_cli",
        description="Print the event-type inventory and field keys of an event log (read-only).",
    )
    parser.add_argument(
        "--events",
        required=True,
        metavar="PATH",
        help="Path to the append-only event log (JSONL) to read.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the inventory as JSON instead of a human-readable listing.",
    )
    args = parser.parse_args(argv)

    store = EventStore(args.events)
    inventory = build_inventory(store.iter_events())

    if args.json:
        print(json.dumps(inventory, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print(_format_text(inventory))
    return 0


if __name__ == "__main__":
    sys.exit(main())

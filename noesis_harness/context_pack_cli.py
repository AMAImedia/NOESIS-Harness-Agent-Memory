"""noesis_harness/context_pack_cli.py

Read-only command-line wrapper around noesis_harness.context_pack and the
recall_augment ranking over the append-only event log.

Patterns adapted from:
  - LoopX (replay projection + read-only context packing)

This is a thin, side-effect-free entry point. It opens an event log read-only,
ranks events by deterministic relevance (recall_augment.rank_events), and prints
a compact context block (or a JSON shape). It never appends, edits, or deletes
any event. All ranking/cache imports are done inside main() so the module stays
importable even when an optional dependency is unavailable.

Design guarantees (see AGENTS.md):
  - Read-only: no write path is opened against the event log.
  - Deterministic: identical args -> identical output.
  - Idempotent: no side effects, safe to re-run.
  - Python 3.9+ syntax: no `X | None`, no `match`.

Zero dependencies (stdlib only): argparse, json, sys.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="context_pack",
        description=(
            "Read-only CLI that ranks events from an append-only event log "
            "and prints a compact context block."
        ),
    )
    parser.add_argument(
        "--events",
        required=True,
        help="Path to the append-only event log (JSONL). Opened read-only.",
    )
    parser.add_argument(
        "--query",
        required=True,
        help="Query string used to rank events by relevance.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=8,
        help="Maximum number of ranked events to include (default: 8).",
    )
    parser.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Print the result as a JSON object instead of a Markdown block.",
    )
    return parser


def _format_markdown(ranked: List[Dict[str, Any]], query: str) -> str:
    """Build a compact Markdown context block from ranked events."""
    if not ranked:
        return "# Context pack\n\n(no matching events)\n"
    lines: List[str] = ["# Context pack", "", "query: " + query, ""]
    for index, item in enumerate(ranked, start=1):
        lines.append(
            "## {0}. [{1}] seq={2} score={3:.4f}".format(
                index, item.get("type", ""), item.get("seq", 0), item.get("score", 0.0)
            )
        )
        lines.append("")
        lines.append("```")
        lines.append(str(item.get("snippet", "")))
        lines.append("```")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point. Returns a process exit code (0 on success).

    Read-only: the event log is opened read-only by recall_augment.rank_events.
    When the optional ranking helper is unavailable, prints a clear message and
    returns a non-zero exit code.
    """
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    try:
        from . import recall_augment  # type: ignore
    except Exception as exc:  # pragma: no cover - defensive
        sys.stderr.write(
            "context_pack: ranking helper recall_augment unavailable: {0}\n".format(exc)
        )
        return 3

    try:
        ranked = recall_augment.rank_events(args.query, args.events, top_k=args.top_k)
    except FileNotFoundError:
        sys.stderr.write(
            "context_pack: event log not found (read-only): {0}\n".format(args.events)
        )
        return 2
    except Exception as exc:  # pragma: no cover - defensive
        sys.stderr.write("context_pack: failed to rank events: {0}\n".format(exc))
        return 1

    if args.as_json:
        payload = {
            "query": args.query,
            "events": args.events,
            "top_k": args.top_k,
            "count": len(ranked),
            "ranked": ranked,
        }
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    else:
        sys.stdout.write(_format_markdown(ranked, args.query))
    return 0


if __name__ == "__main__":
    sys.exit(main())

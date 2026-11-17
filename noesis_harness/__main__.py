"""noesis_harness/__main__.py

Unified, read-only operator front-door for the local-first Agent OS.

Single entry point: `python -m noesis_harness <subcommand>`.

Patterns adapted from:
  - LoopX       (state_projection: a read-only replay surface, never the source of truth)
  - agentmemory (leases.ts: operator-facing TTL/coordination accounting)
  - Hermes      (operator snapshot: a non-mutating control-plane view)

This module wires the existing read-only surfaces (operator_status,
self_audit, recall_augment) into one argparse dispatcher. It adds NO new logic:
every subcommand delegates to the corresponding `main` (or, for recall, to
`build_augmented_context`). The CLI is strictly read-only and append-only safe:
it never appends, mutates, or repairs the event log, the lease store, or any
other state file.

Subcommands:
  status   -> operator_status.main      (--events/--leases/--json)
  audit    -> self_audit.main            (--events/--leases/--json/--strict/--now)
  recall   -> recall_augment.build_augmented_context (--query/--events/--top-k)

Zero dependencies (stdlib only): argparse, sys.
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional


def _build_parser():
    # type: () -> argparse.ArgumentParser
    parser = argparse.ArgumentParser(
        prog="noesis_harness",
        description="NOESIS operator front-door (read-only control-plane surface)")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    p_status = sub.add_parser(
        "status", help="read-only operator health snapshot")
    p_status.add_argument("--events", default=None,
                          help="path to an append-only event log (JSONL)")
    p_status.add_argument("--leases", default=None,
                          help="path to a SQLite coordination store")
    p_status.add_argument("--json", action="store_true",
                          help="emit machine-readable JSON")

    p_audit = sub.add_parser(
        "audit", help="control-plane self-audit (read-only)")
    p_audit.add_argument("--events", default=None,
                         help="path to an append-only event log (JSONL)")
    p_audit.add_argument("--leases", default=None,
                         help="path to a SQLite coordination store")
    p_audit.add_argument("--json", action="store_true",
                         help="emit machine-readable JSON")
    p_audit.add_argument("--strict", action="store_true",
                         help="exit non-zero if any error/critical finding is present")
    p_audit.add_argument("--now", type=float, default=None,
                         help="override 'now' for lease TTL checks (deterministic replay)")

    p_recall = sub.add_parser(
        "recall", help="deterministic retrieval-augmented context over the event log")
    p_recall.add_argument("--query", required=True,
                          help="free-text query to rank events against")
    p_recall.add_argument("--events", required=True,
                          help="path to an append-only event log (JSONL)")
    p_recall.add_argument("--top-k", type=int, default=8,
                          help="maximum number of events to recall (default 8)")

    # `func` is resolved lazily in main() so import errors surface only when the
    # subcommand is actually invoked; all targets are import-safe regardless.
    return parser


def _run_status(args):
    # type: (argparse.Namespace) -> int
    from noesis_harness import operator_status

    argv = []  # type: List[str]
    if args.events:
        argv += ["--events", args.events]
    if args.leases:
        argv += ["--leases", args.leases]
    if args.json:
        argv += ["--json"]
    return operator_status.main(argv)


def _run_audit(args):
    # type: (argparse.Namespace) -> int
    from noesis_harness import self_audit

    argv = []  # type: List[str]
    if args.events:
        argv += ["--events", args.events]
    if args.leases:
        argv += ["--leases", args.leases]
    if args.json:
        argv += ["--json"]
    if args.strict:
        argv += ["--strict"]
    if args.now is not None:
        argv += ["--now", str(args.now)]
    return self_audit.main(argv)


def _run_recall(args):
    # type: (argparse.Namespace) -> int
    from noesis_harness import recall_augment

    context = recall_augment.build_augmented_context(
        args.query, args.events, args.top_k)
    if context:
        print(context)
    return 0


_DISPATCH = {
    "status": _run_status,
    "audit": _run_audit,
    "recall": _run_recall,
}


def main(argv=None):
    # type: (Optional[List[str]]) -> int
    if argv is None:
        argv = sys.argv[1:]
    argv = list(argv)

    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        return int(code) if isinstance(code, int) else 1

    func = _DISPATCH.get(args.command)
    if func is None:
        # No subcommand, or an unknown one: argparse already emitted usage to
        # stderr for the unknown case; report a clean non-zero exit here too.
        if args.command is None:
            parser.print_usage(sys.stderr)
        return 2

    return func(args)


if __name__ == "__main__":
    raise SystemExit(main())

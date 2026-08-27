"""Read-only generic inspector CLI for NOESIS harness state.

Patterns borrowed: LoopX (read-only introspection/inspector tooling that
never mutates the state it observes). The CLI is deliberately a thin,
dependency-light wrapper around existing projection functions:

  --view metrics  -> noesis_harness.metrics_snapshot.snapshot(events_path)
  --view summary  -> noesis_harness.summary_view.summarize(events_path)
  --view leases   -> noesis_harness.self_audit.audit_coordination(db_path)

All three underlying functions are pure/read-only: they never append to the
event log or coordinate store. The CLI adds no mutation surface of its own.
Dependencies are imported lazily inside main() so a missing optional module
degrades gracefully (the affected --view is skipped, not fatal).
"""

import argparse
import json
import sys


def _build_parser(argv):
    parser = argparse.ArgumentParser(
        prog="inspect_cli",
        description="Read-only inspector for NOESIS event logs and coordination store.",
    )
    parser.add_argument(
        "--events",
        default=None,
        help="Path to the JSONL event log (used by --view metrics and summary).",
    )
    parser.add_argument(
        "--leases",
        default=None,
        help="Path to the SQLite coordination/lease store (used by --view leases).",
    )
    parser.add_argument(
        "--view",
        required=True,
        choices=["metrics", "summary", "leases"],
        help="Which read-only projection to compute and print as JSON.",
    )
    return parser.parse_args(argv)


def main(argv=None):
    """Entry point. Returns an int exit code (0 on success).

    Lazily imports the projection module for the requested --view. If that
    module is unavailable, prints a JSON error object for that view and exits 0
    (missing optional deps are skipped, not fatal, to keep the tool usable).
    """
    args = _build_parser(argv if argv is not None else sys.argv[1:])

    if args.view in ("metrics", "summary") and not args.events:
        sys.stderr.write("error: --events is required for --view %s\n" % args.view)
        return 2
    if args.view == "leases" and not args.leases:
        sys.stderr.write("error: --leases is required for --view leases\n")
        return 2

    try:
        if args.view == "metrics":
            from noesis_harness.metrics_snapshot import snapshot

            result = snapshot(args.events)
        elif args.view == "summary":
            from noesis_harness.summary_view import summarize

            result = summarize(args.events)
        else:  # leases
            from noesis_harness.self_audit import audit_coordination

            report = audit_coordination(args.leases)
            result = report.as_dict()
    except ImportError as exc:
        sys.stdout.write(
            json.dumps(
                {"view": args.view, "error": "missing dependency", "detail": str(exc)},
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n"
        )
        return 0

    sys.stdout.write(
        json.dumps(result, ensure_ascii=False, sort_keys=True, default=str, indent=2)
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

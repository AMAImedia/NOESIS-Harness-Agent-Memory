"""noesis_harness/diff_cli.py

Read-only CLI that diffs two projection snapshots produced by
noesis_harness.projection_cache (JSON files written via write_snapshot).

Patterns adapted from:
  - LoopX (snapshot.py: two state projections are compared by key so that a
    reconciliation step can reason about added/removed/changed entries without
    replaying the underlying logs)
  - agentmemory (diff.py: a deterministic key-set diff is the basis for
    merge/sync decisions)

The tool is strictly read-only: it loads two snapshot files via
snapshot_file() and reports the key delta. It never writes or mutates any
state, and it relies only on the standard library (json) plus the project's
own stdlib-only projection_cache module.

Exit codes:
  - 0 on success (including when differences are found)
  - 2 on argument/usage errors (e.g. a snapshot file cannot be read)

Zero dependencies beyond the standard library.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple

from noesis_harness.projection_cache import snapshot_file


def _key_view(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the keyed projection (`by_key`) from a snapshot.

    Falls back to an empty dict when the snapshot has no `by_key` field so the
    diff is still well defined for partial snapshots.
    """
    by_key = snapshot.get("by_key")
    if not isinstance(by_key, dict):
        return {}
    return by_key


def diff_snapshots(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    """Compute the key delta between two projection snapshots.

    Returns a dict with three key sets (lists, sorted for determinism):
      - added:   keys present in `right` but not in `left`
      - removed: keys present in `left` but not in `right`
      - changed: keys present in both whose projected value differs

    The comparison is value-based (JSON equality), so a key whose payload is
    identical across snapshots is neither added, removed, nor changed.
    """
    left_view = _key_view(left)
    right_view = _key_view(right)

    left_keys = set(left_view.keys())
    right_keys = set(right_view.keys())

    added = sorted(right_keys - left_keys)
    removed = sorted(left_keys - right_keys)
    changed = sorted(
        k
        for k in (left_keys & right_keys)
        if not _values_equal(left_view[k], right_view[k])
    )

    return {"added": added, "removed": removed, "changed": changed}


def _values_equal(a: Any, b: Any) -> bool:
    """Structural equality tolerant of dict/int/float/str variations."""
    try:
        return json.dumps(a, sort_keys=True, default=str) == json.dumps(
            b, sort_keys=True, default=str
        )
    except (TypeError, ValueError):
        return a == b


def _format_report(result: Dict[str, Any]) -> str:
    """Render the diff result as human-readable text."""
    lines: List[str] = []
    lines.append(f"added:   {len(result['added'])}")
    for key in result["added"]:
        lines.append(f"  + {key}")
    lines.append(f"removed: {len(result['removed'])}")
    for key in result["removed"]:
        lines.append(f"  - {key}")
    lines.append(f"changed: {len(result['changed'])}")
    for key in result["changed"]:
        lines.append(f"  ~ {key}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="diff_cli",
        description="Read-only diff of two projection snapshots (JSON).",
    )
    parser.add_argument(
        "--left",
        required=True,
        help="Path to the left snapshot JSON file (projection_cache output).",
    )
    parser.add_argument(
        "--right",
        required=True,
        help="Path to the right snapshot JSON file (projection_cache output).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-key detail; print only counts.",
    )
    parser.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Emit the diff as a JSON object instead of text.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point. Returns a process exit code (int)."""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2

    try:
        left = snapshot_file(args.left)
        right = snapshot_file(args.right)
    except (OSError, ValueError) as exc:
        sys.stderr.write(f"diff_cli: cannot read snapshot: {exc}\n")
        return 2

    result = diff_snapshots(left, right)

    if args.as_json:
        sys.stdout.write(json.dumps(result, sort_keys=True, ensure_ascii=False) + "\n")
    elif args.quiet:
        sys.stdout.write(
            f"added: {len(result['added'])} "
            f"removed: {len(result['removed'])} "
            f"changed: {len(result['changed'])}\n"
        )
    else:
        sys.stdout.write(_format_report(result) + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())

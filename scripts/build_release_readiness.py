"""Generate or verify a NOESIS release readiness snapshot offline."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.release_readiness_snapshot import build_snapshot, verify_snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a claim-conservative NOESIS release readiness snapshot")
    parser.add_argument("--audit-json", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--test-count", required=True, type=int)
    parser.add_argument("--python-version", required=True)
    parser.add_argument("--native-status", default="not_run")
    parser.add_argument("--external-status", default="not_run")
    args = parser.parse_args(argv)
    audit = json.loads(Path(args.audit_json).read_text(encoding="utf-8"))
    snapshot = build_snapshot(audit, args.test_count, args.python_version, args.native_status, args.external_status)
    verification = verify_snapshot(snapshot)
    if verification.get("status") != "passed":
        raise SystemExit(2)
    Path(args.output).write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "passed", "snapshot_digest": snapshot["snapshot_digest"], "output": str(Path(args.output).resolve())}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

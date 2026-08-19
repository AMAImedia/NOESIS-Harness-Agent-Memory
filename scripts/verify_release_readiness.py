"""Verify a transferred release-readiness snapshot without executing anything."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.release_readiness_snapshot import verify_snapshot

SCHEMA = "noesis.release-readiness-verification.v1"


def verify_file(path: str | Path) -> dict[str, Any]:
    target = Path(path).resolve()
    if not target.is_file():
        return {"schema_version": SCHEMA, "status": "blocked", "reason": "readiness_snapshot_missing", "automatic_execution": False}
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
        result = verify_snapshot(value)
        return {"schema_version": SCHEMA, "status": result.get("status", "blocked"), "reason": result.get("reason"), "snapshot_digest": result.get("snapshot_digest", ""), "overall_status": result.get("overall_status"), "automatic_execution": False, "external_execution_claim": False}
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return {"schema_version": SCHEMA, "status": "blocked", "reason": type(exc).__name__ + ":" + str(exc)[:160], "automatic_execution": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a NOESIS release-readiness snapshot offline")
    parser.add_argument("--snapshot", required=True)
    args = parser.parse_args(argv)
    result = verify_file(args.snapshot)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("status") == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())

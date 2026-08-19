"""Run the bounded NOESIS release gate over transferred evidence.

The gate composes existing offline checks only. It never reruns generation,
executes providers, launches child processes, or makes network requests.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.post_transfer_audit import audit as audit_transfer
from scripts.release_gate_artifact import build_gate_artifact
from scripts.verify_release_readiness import verify_file

SCHEMA = "noesis.release-gate.v1"


def run_gate(root: str | Path, key: str, snapshot: str | Path) -> dict[str, Any]:
    transfer = audit_transfer(root, key)
    if transfer.get("status") != "passed":
        return {"schema_version": SCHEMA, "status": "blocked", "failed_stage": "post_transfer_audit", "stages": {"post_transfer_audit": transfer}, "automatic_execution": False, "external_execution_claim": False}
    readiness = verify_file(snapshot)
    if readiness.get("status") != "passed":
        return {"schema_version": SCHEMA, "status": "blocked", "failed_stage": "release_readiness_snapshot", "stages": {"post_transfer_audit": transfer, "release_readiness_snapshot": readiness}, "automatic_execution": False, "external_execution_claim": False}
    return {"schema_version": SCHEMA, "status": "passed", "stages": {"post_transfer_audit": transfer, "release_readiness_snapshot": readiness}, "automatic_execution": False, "external_execution_claim": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run NOESIS release gate offline")
    parser.add_argument("--root", required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--output", help="Optional path for a deterministic release-gate artifact")
    args = parser.parse_args(argv)
    try:
        result = run_gate(args.root, args.key, args.snapshot)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        result = {"schema_version": SCHEMA, "status": "blocked", "failed_stage": "input", "reason": type(exc).__name__ + ":" + str(exc)[:160], "automatic_execution": False, "external_execution_claim": False}
    if args.output:
        output = Path(args.output).resolve()
        output.write_text(json.dumps(build_gate_artifact(result), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("status") == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())

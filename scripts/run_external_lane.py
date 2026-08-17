#!/usr/bin/env python3
"""Prepare or execute a pinned external lane with explicit operator approval."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.pinned_runner_adapter import RunnerConfigurationError, execute, validate


def plan(spec: dict[str, Any], workspace: str) -> dict[str, Any]:
    argv, root, environment = validate(spec, workspace)
    command_digest = hashlib.sha256(json.dumps(argv, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {
        "schema_version": "noesis.external-lane-plan.v1",
        "execution": "not_started",
        "system": spec["system"],
        "revision": spec["revision"],
        "protocol_fingerprint": spec["protocol_fingerprint"],
        "workspace": str(root),
        "command_sha256": command_digest,
        "argv_length": len(argv),
        "environment_keys": sorted(environment),
        "approval_required": True,
        "reason": "dry_run_only",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Plan or explicitly execute a pinned NOESIS external lane")
    parser.add_argument("--spec", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--approve", action="store_true")
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args(argv)
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    try:
        report = plan(spec, args.workspace)
        if args.execute:
            if not args.approve:
                raise PermissionError("--execute requires --approve")
            outcome = execute(spec, args.workspace, approval=True, timeout=args.timeout)
            report.update({"execution": "started", "status": outcome.status, "returncode": outcome.returncode, "stdout": outcome.stdout, "stderr": outcome.stderr, "timed_out": outcome.timed_out})
    except (RunnerConfigurationError, PermissionError) as exc:
        report = {"schema_version": "noesis.external-lane-plan.v1", "execution": "denied", "status": "not_run", "reason": str(exc)}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": args.output, "execution": report["execution"], "status": report.get("status", "not_run")}, ensure_ascii=False))
    return 0 if report["execution"] == "not_started" or report.get("status") == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())

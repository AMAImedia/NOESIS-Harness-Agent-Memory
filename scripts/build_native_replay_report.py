"""Build a fail-closed native artifact replay report without executing artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from noesis_harness.native_parity import validate_native_artifacts

SCHEMA = "noesis.native-artifact-replay.v1"


def build_report(target: str, evidence_dir: str, *, current_platform: str, python_version: tuple[int, int, int]) -> dict[str, Any]:
    evidence = validate_native_artifacts(target, evidence_dir, current_platform=current_platform, python_version=python_version)
    status = evidence.status
    return {
        "schema_version": SCHEMA,
        "target": target,
        "status": status,
        "reason": evidence.reason,
        "platform": evidence.platform,
        "python_version": evidence.python_version,
        "environment_digest": evidence.environment_digest,
        "artifact_replay_allowed": status == "passed",
        "execution_performed": False,
        "native_execution_claim": False,
        "external_execution_claim": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build native artifact replay report without executing artifacts")
    parser.add_argument("--target", required=True, choices=("windows", "macos"))
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--python-version", required=True, help="major.minor.patch")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    version = tuple(int(part) for part in args.python_version.split("."))
    report = build_report(args.target, args.evidence_dir, current_platform=args.platform, python_version=version)  # type: ignore[arg-type]
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": args.output, "status": report["status"], "artifact_replay_allowed": report["artifact_replay_allowed"]}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())

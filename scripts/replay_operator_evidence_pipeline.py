"""Patterns adapted from NOESIS reproducibility receipts and operator evidence gates.

This module replays the bounded evidence pipeline into an explicitly empty output
root and compares deterministic artifact bytes without launching providers,
network requests, or child runtimes.
"""
from __future__ import annotations

import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Any

from scripts.post_transfer_audit import audit as post_transfer_audit
from scripts.release_gate import run_gate
from scripts.run_operator_evidence_pipeline import run_pipeline

SCHEMA = "noesis.operator-evidence-clean-room-replay.v1"
COMPARE_FILES = (
    "external-evidence-readiness.json",
    "signed-external-evidence-aggregate.json",
    "artifact-manifest.json",
    "verification-result.json",
    "chain-summary.json",
    "reproducibility-receipt.json",
    "release-readiness.json",
    "release-gate.json",
    "signed-readiness-receipt.json",
)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _runtime_fingerprint() -> dict[str, str]:
    return {"python_implementation": platform.python_implementation(), "python_version": "%d.%d.%d" % sys.version_info[:3], "platform_system": platform.system(), "platform_machine": platform.machine()}


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("replay_json_object_required:" + path.name)
    return value


def replay_clean_room(expected_root: str | Path, manifest_path: str, evidence_paths: list[str], key: str, replay_root: str | Path, readiness_test_count: int | None = None, readiness_python_version: str | None = None, native_status: str = "not_run", external_status: str = "not_run") -> dict[str, Any]:
    expected = Path(expected_root).resolve()
    replay = Path(replay_root).resolve()
    if not expected.is_dir():
        return {"schema_version": SCHEMA, "status": "blocked", "reason": "expected_root_missing", "automatic_execution": False}
    replay.mkdir(parents=True, exist_ok=True)
    if any(replay.iterdir()):
        return {"schema_version": SCHEMA, "status": "blocked", "reason": "replay_root_not_clean", "automatic_execution": False}
    try:
        pipeline = run_pipeline(manifest_path, evidence_paths, key, str(replay), readiness_test_count=readiness_test_count, readiness_python_version=readiness_python_version, native_status=native_status, external_status=external_status)
        expected_files = [name for name in COMPARE_FILES if (expected / name).is_file()]
        replay_files = [name for name in COMPARE_FILES if (replay / name).is_file()]
        if "reproducibility-receipt.json" in expected_files:
            expected_receipt = _read(expected / "reproducibility-receipt.json")
            replay_receipt = _read(replay / "reproducibility-receipt.json")
            expected_runtime = expected_receipt.get("runtime_fingerprint", {})
            replay_runtime = replay_receipt.get("runtime_fingerprint", {})
            if expected_runtime != replay_runtime:
                return {"schema_version": SCHEMA, "status": "blocked", "reason": "runtime_fingerprint_drift", "expected": expected_runtime, "replayed": replay_runtime, "automatic_execution": False}
            if replay_runtime != _runtime_fingerprint():
                return {"schema_version": SCHEMA, "status": "blocked", "reason": "runtime_fingerprint_environment_mismatch", "receipt": replay_runtime, "actual": _runtime_fingerprint(), "automatic_execution": False}
        if "release-readiness.json" in expected_files:
            expected_snapshot = _read(expected / "release-readiness.json")
            for field in ("native_host_status", "external_lanes_status"):
                if expected_snapshot.get(field) == "passed":
                    return {"schema_version": SCHEMA, "status": "blocked", "reason": "host_dependent_lane_replay_requires_receipts", "lane": field, "automatic_execution": False}
        if expected_files != replay_files:
            return {"schema_version": SCHEMA, "status": "blocked", "reason": "replay_artifact_set_mismatch", "expected": expected_files, "replayed": replay_files, "automatic_execution": False}
        mismatches = {name: {"expected": _digest(expected / name), "replayed": _digest(replay / name)} for name in expected_files if _digest(expected / name) != _digest(replay / name)}
        if mismatches:
            return {"schema_version": SCHEMA, "status": "blocked", "reason": "replay_digest_mismatch", "mismatches": mismatches, "automatic_execution": False}
        strict = post_transfer_audit(replay, key)
        if strict.get("status") != "passed":
            return {"schema_version": SCHEMA, "status": "blocked", "reason": "replayed_post_transfer_blocked", "post_transfer": strict, "automatic_execution": False}
        gate = None
        if (replay / "release-readiness.json").is_file():
            gate = run_gate(replay, key, replay / "release-readiness.json")
            if gate.get("status") != "passed":
                return {"schema_version": SCHEMA, "status": "blocked", "reason": "replayed_release_gate_blocked", "release_gate": gate, "automatic_execution": False}
        return {"schema_version": SCHEMA, "status": "passed", "pipeline_status": pipeline.get("status"), "compared_files": expected_files, "post_transfer_status": strict.get("status"), "release_gate_status": gate.get("status") if gate else "not_run", "automatic_execution": False, "external_execution_claim": False}
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return {"schema_version": SCHEMA, "status": "blocked", "reason": type(exc).__name__ + ":" + str(exc)[:160], "automatic_execution": False}


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Replay a NOESIS evidence pipeline in an empty output root")
    parser.add_argument("--expected-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--evidence", nargs="+", required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--replay-root", required=True)
    parser.add_argument("--readiness-test-count", type=int)
    parser.add_argument("--readiness-python-version")
    parser.add_argument("--native-status", default="not_run")
    parser.add_argument("--external-status", default="not_run")
    args = parser.parse_args(argv)
    result = replay_clean_room(args.expected_root, args.manifest, args.evidence, args.key, args.replay_root, args.readiness_test_count, args.readiness_python_version, args.native_status, args.external_status)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("status") == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())

__all__ = ["replay_clean_room"]

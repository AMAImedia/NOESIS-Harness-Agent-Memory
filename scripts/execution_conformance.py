"""Patterns adapted from NOESIS readiness matrices, signed receipts, and host-boundary gates.

This module projects existing evidence into separate execution classes. It never
executes a provider, host sandbox, network request, or child runtime.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "noesis.execution-conformance.v1"
STATUSES = ("passed", "not_run", "blocked", "unsupported")


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _status(value: Any) -> str:
    return str(value) if str(value) in STATUSES else "blocked"


def build_conformance(snapshot: Mapping[str, Any], matrix: Mapping[str, Any], replay: Mapping[str, Any], gate: Mapping[str, Any]) -> dict[str, Any]:
    local_status = _status(replay.get("status"))
    native_status = _status(snapshot.get("native_host_status", "not_run"))
    external_status = _status(snapshot.get("external_lanes_status", "not_run"))
    reasons: list[str] = []
    if local_status == "passed" and (replay.get("post_transfer_status") != "passed" or replay.get("release_gate_status") != "passed"):
        local_status, reasons = "blocked", reasons + ["local_replay_supporting_gates_missing"]
    if native_status == "passed" and snapshot.get("claims", {}).get("native_execution") is not True:
        native_status, reasons = "blocked", reasons + ["native_status_claim_mismatch"]
    if external_status == "passed" and (snapshot.get("claims", {}).get("external_execution") is not True or matrix.get("overall_status") != "passed" or matrix.get("comparative_ready") is not True):
        external_status, reasons = "blocked", reasons + ["external_status_matrix_mismatch"]
    if gate.get("status") != "passed" and (local_status == "passed" or native_status == "passed" or external_status == "passed"):
        reasons.append("release_gate_not_passed")
        if local_status == "passed":
            local_status = "blocked"
    statuses = {"local_replay": local_status, "native_host": native_status, "external_lanes": external_status}
    if reasons:
        overall = "blocked"
    elif all(value == "passed" for value in statuses.values()):
        overall = "passed"
    elif all(value == "unsupported" for value in statuses.values()):
        overall = "unsupported"
    else:
        overall = "not_run"
    unsigned = {
        "schema_version": SCHEMA,
        "overall_status": overall,
        "execution_classes": {
            "local_replay": {"status": local_status, "evidence_basis": "clean_room_replay_and_final_gate"},
            "native_host": {"status": native_status, "evidence_basis": "host_bound_readiness_receipt_required"},
            "external_lanes": {"status": external_status, "evidence_basis": "signed_lane_matrix_and_comparative_receipt_required"},
        },
        "reasons": reasons,
        "claims": {"local_replay": local_status == "passed", "native_execution": native_status == "passed", "external_execution": external_status == "passed", "worldwide_superiority": False},
        "automatic_execution": False,
        "execution_claim": "evidence_projection_only",
        "claim_boundary": "execution_conformance_summary_only",
    }
    return {**unsigned, "conformance_digest": hashlib.sha256(_canonical(unsigned)).hexdigest()}


def verify_conformance(report: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(report, Mapping) or report.get("schema_version") != SCHEMA:
        return {"status": "blocked", "reason": "conformance_schema_invalid"}
    unsigned = {key: report[key] for key in report if key != "conformance_digest"}
    if report.get("conformance_digest") != hashlib.sha256(_canonical(unsigned)).hexdigest():
        return {"status": "blocked", "reason": "conformance_digest_mismatch"}
    if report.get("automatic_execution") is not False or report.get("claim_boundary") != "execution_conformance_summary_only" or report.get("claims", {}).get("worldwide_superiority") is not False:
        return {"status": "blocked", "reason": "conformance_claim_boundary_invalid"}
    return {"status": "passed", "conformance_digest": str(report["conformance_digest"]), "overall_status": str(report.get("overall_status"))}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build NOESIS execution conformance projection")
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--matrix", required=True)
    parser.add_argument("--replay", required=True)
    parser.add_argument("--gate", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    read = lambda path: json.loads(Path(path).read_text(encoding="utf-8"))
    report = build_conformance(read(args.snapshot), read(args.matrix), read(args.replay), read(args.gate))
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["overall_status"], "output": args.output, "conformance_digest": report["conformance_digest"]}, ensure_ascii=False, sort_keys=True))
    return 0 if report["overall_status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())

__all__ = ["build_conformance", "verify_conformance"]

"""Patterns adapted from NOESIS readiness matrices, signed receipts, and host-boundary gates.

This module projects existing evidence into separate execution classes. It never
executes a provider, host sandbox, network request, or child runtime. The
backend_verification section additionally projects the ExecutionBackend /
verify_backend_or_block honesty contract (Gate 3, parity with
run_sandbox_conformance) using local stub backends only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from noesis_harness.execution_assurance import ExecutionBackend, verify_backend_or_block  # noqa: E402

SCHEMA = "noesis.execution-conformance.v1"
STATUSES = ("passed", "not_run", "blocked", "unsupported")


class BackendVerificationHonestyError(ValueError):
    """Raised fail-closed when a backend verification entry claims passed."""


class _ConformanceFailingBackend(ExecutionBackend):
    """Local stub whose isolation verification fails; never executes anything."""

    def verify_isolation(self) -> Mapping[str, Any]:
        return {"status": "blocked", "reason": "isolation_verification_refused"}

    def execute(self, request: Mapping[str, Any], policy: Mapping[str, Any]) -> Mapping[str, Any]:
        raise NotImplementedError("execution_forbidden_in_conformance_projection")


class _ConformanceUnavailableBackend(ExecutionBackend):
    """Local stub standing in for a missing platform runtime; never executes."""

    def verify_isolation(self) -> Mapping[str, Any]:
        return {"status": "unavailable", "reason": "backend_runtime_unavailable"}

    def execute(self, request: Mapping[str, Any], policy: Mapping[str, Any]) -> Mapping[str, Any]:
        raise NotImplementedError("execution_forbidden_in_conformance_projection")


def _default_backend_plan() -> tuple:
    return (
        ("unconfigured_none", None, "not_run", "backend_not_configured"),
        ("failing_stub", _ConformanceFailingBackend("conformance-failing-stub"), "blocked", "isolation_verification_refused"),
        ("unavailable_stub", _ConformanceUnavailableBackend("conformance-unavailable-stub"), "unavailable", "backend_runtime_unavailable"),
    )


def build_backend_verification_section(plan: Optional[Any] = None) -> dict[str, Any]:
    """Project the ExecutionBackend/verify_backend_or_block contract honestly.

    Each plan entry is (backend_name, backend_or_None, expected_status,
    expected_reason). A passed result from any backend raises fail-closed;
    the section is passed only when every entry matches its expected honest
    non-passed status and reason.
    """
    entries: list[dict[str, str]] = []
    reasons: list[str] = []
    resolved = _default_backend_plan() if plan is None else tuple(plan)
    for name, backend, expected_status, expected_reason in resolved:
        result = verify_backend_or_block(backend)
        status = str(result.get("status"))
        reason = str(result.get("reason", ""))
        if status == "passed":
            raise BackendVerificationHonestyError("backend_verification_unexpected_passed:" + str(name))
        entries.append({"backend": str(name), "status": status, "reason": reason})
        if status != str(expected_status) or reason != str(expected_reason):
            reasons.append(str(name) + "_honest_status_mismatch")
    section = {
        "status": "blocked" if reasons else "passed",
        "entries": entries,
        "reasons": reasons,
        "evidence_basis": "local_verify_backend_or_block_contract_projection",
    }
    return section


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
        "backend_verification": build_backend_verification_section(),
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

"""Build a claim-conservative NOESIS release readiness snapshot.

The snapshot summarizes existing evidence only. It never promotes not-run or
blocked native/external lanes to passed and never executes a provider.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

SCHEMA = "noesis.release-readiness-snapshot.v1"
STATUS_VALUES = ("passed", "not_run", "blocked", "unsupported")


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def build_snapshot(audit: Mapping[str, Any], test_count: int, python_version: str, native_status: str = "not_run", external_status: str = "not_run") -> dict[str, Any]:
    if test_count < 0:
        raise ValueError("test_count_must_be_non_negative")
    if native_status not in STATUS_VALUES or external_status not in STATUS_VALUES:
        raise ValueError("invalid_readiness_status")
    audit_status = str(audit.get("status", "blocked"))
    overall = "passed" if audit_status == "passed" and test_count > 0 else "blocked"
    unsigned = {
        "schema_version": SCHEMA,
        "overall_status": overall,
        "post_transfer_audit_status": audit_status,
        "validated_test_count": int(test_count),
        "python_version": str(python_version),
        "native_host_status": native_status,
        "external_lanes_status": external_status,
        "claims": {
            "local_evidence_integrity": audit_status == "passed",
            "native_execution": False,
            "external_execution": False,
            "worldwide_superiority": False,
        },
        "blockers": [
            "matching_native_windows_macos_hosts_required" if native_status != "passed" else "",
            "pinned_external_lane_receipts_required" if external_status != "passed" else "",
        ],
        "automatic_execution": False,
        "claim_boundary": "release_readiness_summary_only",
    }
    unsigned["blockers"] = [item for item in unsigned["blockers"] if item]
    return {**unsigned, "snapshot_digest": hashlib.sha256(_canonical(unsigned)).hexdigest()}


def verify_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(snapshot, Mapping) or snapshot.get("schema_version") != SCHEMA:
        return {"status": "blocked", "reason": "readiness_snapshot_schema_invalid"}
    unsigned = {name: snapshot[name] for name in snapshot if name != "snapshot_digest"}
    if snapshot.get("snapshot_digest") != hashlib.sha256(_canonical(unsigned)).hexdigest():
        return {"status": "blocked", "reason": "readiness_snapshot_digest_mismatch"}
    if snapshot.get("automatic_execution") is not False or snapshot.get("claim_boundary") != "release_readiness_summary_only":
        return {"status": "blocked", "reason": "readiness_snapshot_claim_boundary_invalid"}
    if snapshot.get("native_host_status") != "passed" and snapshot.get("claims", {}).get("native_execution") is not False:
        return {"status": "blocked", "reason": "native_claim_boundary_invalid"}
    if snapshot.get("external_lanes_status") != "passed" and snapshot.get("claims", {}).get("external_execution") is not False:
        return {"status": "blocked", "reason": "external_claim_boundary_invalid"}
    return {"status": "passed", "snapshot_digest": str(snapshot["snapshot_digest"]), "overall_status": str(snapshot.get("overall_status"))}

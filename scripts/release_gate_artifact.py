"""Build and verify a portable release-gate result artifact."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

SCHEMA = "noesis.release-gate-artifact.v1"


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def build_gate_artifact(result: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = {
        "schema_version": SCHEMA,
        "status": str(result.get("status", "blocked")),
        "failed_stage": result.get("failed_stage"),
        "stages": result.get("stages", {}),
        "automatic_execution": False,
        "external_execution_claim": False,
        "claim_boundary": "release_gate_integrity_summary_only",
    }
    return {**unsigned, "artifact_digest": hashlib.sha256(_canonical(unsigned)).hexdigest()}


def verify_gate_artifact(artifact: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(artifact, Mapping) or artifact.get("schema_version") != SCHEMA:
        return {"status": "blocked", "reason": "release_gate_artifact_schema_invalid"}
    unsigned = {name: artifact[name] for name in artifact if name != "artifact_digest"}
    if artifact.get("artifact_digest") != hashlib.sha256(_canonical(unsigned)).hexdigest():
        return {"status": "blocked", "reason": "release_gate_artifact_digest_mismatch"}
    if artifact.get("automatic_execution") is not False or artifact.get("external_execution_claim") is not False or artifact.get("claim_boundary") != "release_gate_integrity_summary_only":
        return {"status": "blocked", "reason": "release_gate_artifact_claim_boundary_invalid"}
    return {"status": "passed", "artifact_digest": str(artifact["artifact_digest"]), "gate_status": str(artifact.get("status"))}

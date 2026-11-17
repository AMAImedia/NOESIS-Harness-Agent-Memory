"""Registry and fail-closed verifier for committed NOESIS evidence artifacts.

Patterns are adapted from artifact inventories, signed offline verification,
fail-closed evidence projections, and operator transfer audits (agentmemory
fail-closed status surfaces; LoopX append-only conventions). The registry is
declarative metadata plus read-only verification: it never executes, imports,
or rewrites a listed artifact.

This is the canonical list of committed evidence documents included in the
auditable chain. Registration is additive with an explicit verification method
per entry so machine-readable evidence agrees across chain surfaces:

- workload-evidence: self-attesting output_digest, re-verified by recomputing
  the digest via scripts.run_workload_evidence.canonical_digest (imported, not
  duplicated).
- release-audit-evidence: no self-digest exists in the document, so only its
  structure is checked (schema, lane statuses, workspace and result counts);
  every result carries reason "structural_only_no_self_digest" to keep the
  honesty boundary explicit.
"""
from __future__ import annotations

import hmac
import json
from pathlib import Path
from typing import Any, Mapping

from scripts.run_workload_evidence import canonical_digest

SCHEMA = "noesis.committed-evidence-registry.v1"

STATUS_PASSED = "passed"
STATUS_BLOCKED = "blocked"
STATUS_ABSENT = "absent"

WORKLOAD_EVIDENCE_ID = "workload-evidence"
WORKLOAD_EVIDENCE_PATH = "docs/MULTI_AGENT_WORKLOAD_EVIDENCE.json"
WORKLOAD_EVIDENCE_SCHEMA = "noesis.workload-evidence.v1"
WORKLOAD_VERIFICATION_METHOD = "recomputed_output_digest"

RELEASE_AUDIT_EVIDENCE_ID = "release-audit-evidence"
RELEASE_AUDIT_EVIDENCE_PATH = "docs/PARALLEL_RELEASE_AUDIT_EVIDENCE.json"
RELEASE_AUDIT_EVIDENCE_SCHEMA = "noesis.parallel-release-audit.v1"
RELEASE_AUDIT_VERIFICATION_METHOD = "structural_check_only"
STRUCTURAL_ONLY_REASON = "structural_only_no_self_digest"

RELEASE_AUDIT_EXPECTED_WORKSPACES = 5
RELEASE_AUDIT_EXPECTED_RESULTS = 5

COMMITTED_EVIDENCE_ARTIFACTS: tuple[Mapping[str, Any], ...] = (
    {
        "artifact_id": WORKLOAD_EVIDENCE_ID,
        "path": WORKLOAD_EVIDENCE_PATH,
        "expected_schema_version": WORKLOAD_EVIDENCE_SCHEMA,
        "verification_method": WORKLOAD_VERIFICATION_METHOD,
        "reason": "",
    },
    {
        "artifact_id": RELEASE_AUDIT_EVIDENCE_ID,
        "path": RELEASE_AUDIT_EVIDENCE_PATH,
        "expected_schema_version": RELEASE_AUDIT_EVIDENCE_SCHEMA,
        "verification_method": RELEASE_AUDIT_VERIFICATION_METHOD,
        "reason": STRUCTURAL_ONLY_REASON,
    },
)

REGISTERED_FILENAMES = frozenset(Path(str(entry["path"])).name for entry in COMMITTED_EVIDENCE_ARTIFACTS)


def _read_object(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("artifact_json_object_required")
    return value


def _failure(artifact_id: str, method: str, reason: str, extra_reason: str = "") -> dict[str, Any]:
    result = {"artifact_id": artifact_id, "verification_method": method, "status": STATUS_BLOCKED, "reason": reason}
    if extra_reason:
        result["entry_reason"] = extra_reason
    return result


def verify_workload_evidence(path: Path) -> dict[str, Any]:
    """Re-verify the workload artifact's self-attested output_digest."""
    try:
        document = _read_object(path)
    except FileNotFoundError:
        return _failure(WORKLOAD_EVIDENCE_ID, WORKLOAD_VERIFICATION_METHOD, "artifact_missing")
    except IsADirectoryError:
        return _failure(WORKLOAD_EVIDENCE_ID, WORKLOAD_VERIFICATION_METHOD, "artifact_is_directory")
    except OSError:
        return _failure(WORKLOAD_EVIDENCE_ID, WORKLOAD_VERIFICATION_METHOD, "artifact_unreadable")
    except (UnicodeDecodeError, ValueError):
        return _failure(WORKLOAD_EVIDENCE_ID, WORKLOAD_VERIFICATION_METHOD, "artifact_json_invalid")
    if document.get("schema_version") != WORKLOAD_EVIDENCE_SCHEMA:
        return _failure(WORKLOAD_EVIDENCE_ID, WORKLOAD_VERIFICATION_METHOD, "workload_schema_mismatch")
    stored = document.get("output_digest")
    if not isinstance(stored, str) or not stored:
        return _failure(WORKLOAD_EVIDENCE_ID, WORKLOAD_VERIFICATION_METHOD, "output_digest_missing")
    payload = {key: value for key, value in document.items() if key != "output_digest"}
    recomputed = canonical_digest(payload)
    if not hmac.compare_digest(recomputed, stored):
        return _failure(WORKLOAD_EVIDENCE_ID, WORKLOAD_VERIFICATION_METHOD, "workload_output_digest_mismatch")
    return {
        "artifact_id": WORKLOAD_EVIDENCE_ID,
        "verification_method": WORKLOAD_VERIFICATION_METHOD,
        "status": STATUS_PASSED,
        "reason": "",
        "output_digest": stored,
    }


def verify_release_audit_evidence(path: Path) -> dict[str, Any]:
    """Structure-only check for the release-audit artifact (it has no self-digest)."""

    def blocked(reason: str) -> dict[str, Any]:
        return _failure(RELEASE_AUDIT_EVIDENCE_ID, RELEASE_AUDIT_VERIFICATION_METHOD, reason, STRUCTURAL_ONLY_REASON)

    try:
        document = _read_object(path)
    except FileNotFoundError:
        return blocked("artifact_missing")
    except IsADirectoryError:
        return blocked("artifact_is_directory")
    except OSError:
        return blocked("artifact_unreadable")
    except (UnicodeDecodeError, ValueError):
        return blocked("artifact_json_invalid")
    if document.get("schema_version") != RELEASE_AUDIT_EVIDENCE_SCHEMA:
        return blocked("release_audit_schema_mismatch")
    results = document.get("results")
    if not isinstance(results, list):
        return blocked("results_invalid")
    if len(results) != RELEASE_AUDIT_EXPECTED_RESULTS:
        return blocked("results_count_mismatch")
    if document.get("workspace_count") != RELEASE_AUDIT_EXPECTED_WORKSPACES:
        return blocked("workspace_count_mismatch")
    for item in results:
        if not isinstance(item, Mapping) or item.get("status") != STATUS_PASSED:
            return blocked("release_audit_lane_not_passed")
    return {
        "artifact_id": RELEASE_AUDIT_EVIDENCE_ID,
        "verification_method": RELEASE_AUDIT_VERIFICATION_METHOD,
        "status": STATUS_PASSED,
        "reason": STRUCTURAL_ONLY_REASON,
        "result_count": len(results),
        "workspace_count": RELEASE_AUDIT_EXPECTED_WORKSPACES,
    }


def _resolve_entry_path(root: Path, entry: Mapping[str, Any], flat_layout: bool) -> Path:
    relative = str(entry["path"])
    name = Path(relative).name if flat_layout else relative
    return root / name


def verify_committed_evidence(root: str | Path, require_all: bool = True, flat_layout: bool = False) -> dict[str, Any]:
    """Verify registered artifacts under root; fail closed, never raises.

    With require_all=True a missing registered artifact blocks. With
    require_all=False absent entries are reported as status "absent" and do
    not affect the overall status, so optional chain members can be verified
    only when present. With flat_layout=True entries are resolved by filename
    directly under root (transferred artifact sets are flat; repository roots
    use the docs/-relative registry paths).
    """
    base = Path(root)
    artifacts: dict[str, Any] = {}
    for entry in COMMITTED_EVIDENCE_ARTIFACTS:
        path = _resolve_entry_path(base, entry, flat_layout)
        reported = path.name if flat_layout else str(entry["path"])
        if not path.is_file() and not require_all:
            artifacts[str(entry["artifact_id"])] = {
                "artifact_id": entry["artifact_id"],
                "verification_method": entry["verification_method"],
                "status": STATUS_ABSENT,
                "reason": "",
                "path": reported,
            }
            continue
        if str(entry["verification_method"]) == WORKLOAD_VERIFICATION_METHOD:
            check = verify_workload_evidence(path)
        else:
            check = verify_release_audit_evidence(path)
        check["path"] = reported
        artifacts[str(entry["artifact_id"])] = check
    checks = [dict(value) for value in artifacts.values()]
    if any(item["status"] == STATUS_BLOCKED for item in checks):
        overall = STATUS_BLOCKED
    elif all(item["status"] == STATUS_ABSENT for item in checks):
        overall = STATUS_ABSENT
    else:
        overall = STATUS_PASSED
    return {
        "schema_version": SCHEMA,
        "status": overall,
        "artifacts": artifacts,
        "automatic_execution": False,
    }


__all__ = [
    "SCHEMA",
    "COMMITTED_EVIDENCE_ARTIFACTS",
    "REGISTERED_FILENAMES",
    "STRUCTURAL_ONLY_REASON",
    "verify_committed_evidence",
    "verify_release_audit_evidence",
    "verify_workload_evidence",
]

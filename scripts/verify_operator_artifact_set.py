"""Verify a transferred NOESIS operator artifact set without executing contents.

Patterns are adapted from signed report bundle verification, external readiness
verification, signed aggregate verification, and artifact inventory checks. The
verifier reads JSON and ZIP metadata only; it never executes, imports, launches,
or contacts anything described by the artifacts.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from noesis_harness.report_bundle import verify_report_bundle
from scripts.artifact_inventory import verify_inventory
from scripts.aggregate_external_evidence import verify_aggregate
from scripts.signed_verification_result import sign_verification_result, verify_signed_verification_result

SCHEMA = "noesis.operator-artifact-set-verification.v1"


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("artifact_json_object_required")
    return value


def verify_artifact_set(root: str | Path, key: str, report_path: str | None = None) -> dict[str, Any]:
    base = Path(root).resolve()
    if not base.is_dir():
        return {"schema_version": SCHEMA, "status": "blocked", "reason": "artifact_root_missing", "automatic_execution": False}
    manifest_path = base / "artifact-manifest.json"
    if not manifest_path.is_file():
        return {"schema_version": SCHEMA, "status": "blocked", "reason": "artifact_manifest_missing", "automatic_execution": False}
    try:
        inventory = _read(manifest_path)
        inventory_result = verify_inventory(inventory, base, key)
        checks: dict[str, Any] = {"inventory": inventory_result}
        if inventory_result.get("status") != "passed":
            return {"schema_version": SCHEMA, "status": "blocked", "checks": checks, "automatic_execution": False}
        matrix_path = base / "external-evidence-readiness.json"
        aggregate_path = base / "signed-external-evidence-aggregate.json"
        if not matrix_path.is_file() or not aggregate_path.is_file():
            return {"schema_version": SCHEMA, "status": "blocked", "reason": "required_artifact_missing", "checks": checks, "automatic_execution": False}
        matrix = _read(matrix_path)
        aggregate = _read(aggregate_path)
        checks["readiness_matrix"] = {"status": "passed" if matrix.get("schema_version") == "noesis.external-evidence-readiness.v1" else "blocked"}
        checks["aggregate"] = verify_aggregate(aggregate, key)
        if checks["readiness_matrix"]["status"] != "passed" or checks["aggregate"].get("status") != "passed":
            return {"schema_version": SCHEMA, "status": "blocked", "checks": checks, "automatic_execution": False}
        if matrix.get("matrix_digest") != aggregate.get("matrix_digest"):
            checks["cross_artifact_binding"] = {"status": "blocked", "reason": "matrix_digest_mismatch"}
            return {"schema_version": SCHEMA, "status": "blocked", "checks": checks, "automatic_execution": False}
        checks["cross_artifact_binding"] = {"status": "passed"}
        signed_result_path = base / "verification-result.json"
        if signed_result_path.is_file():
            signed_result = _read(signed_result_path)
            signed_result_check = verify_signed_verification_result(signed_result, key)
            checks["signed_verification_result"] = signed_result_check
            if signed_result_check.get("status") != "passed":
                return {"schema_version": SCHEMA, "status": "blocked", "checks": checks, "automatic_execution": False}
            if signed_result.get("inventory_digest") != inventory_result.get("inventory_digest"):
                checks["signed_result_binding"] = {"status": "blocked", "reason": "verification_inventory_digest_mismatch"}
                return {"schema_version": SCHEMA, "status": "blocked", "checks": checks, "automatic_execution": False}
            if signed_result.get("verification_status") != str(aggregate.get("overall_status", "blocked")):
                checks["signed_result_binding"] = {"status": "blocked", "reason": "verification_status_mismatch"}
                return {"schema_version": SCHEMA, "status": "blocked", "checks": checks, "automatic_execution": False}
            checks["signed_result_binding"] = {"status": "passed", "inventory_digest": inventory_result.get("inventory_digest")}
        if report_path:
            report = Path(report_path).resolve()
            if base not in report.parents or not report.is_file():
                return {"schema_version": SCHEMA, "status": "blocked", "reason": "report_path_invalid", "checks": checks, "automatic_execution": False}
            report_result = verify_report_bundle(report, key.encode("utf-8"))
            checks["report_bundle"] = {"status": report_result.get("status", "blocked"), "bundle_digest": report_result.get("bundle_digest", "")}
            if report_result.get("status") != "passed":
                return {"schema_version": SCHEMA, "status": "blocked", "checks": checks, "automatic_execution": False}
        status = str(aggregate.get("overall_status", "blocked"))
        return {"schema_version": SCHEMA, "status": status, "comparative_ready": bool(aggregate.get("comparative_ready")), "checks": checks, "automatic_execution": False, "external_execution_claim": False}
    except (OSError, ValueError, json.JSONDecodeError, TypeError) as exc:
        return {"schema_version": SCHEMA, "status": "blocked", "reason": type(exc).__name__ + ":" + str(exc)[:160], "automatic_execution": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a transferred NOESIS operator artifact set offline")
    parser.add_argument("--root", required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--report")
    parser.add_argument("--signed-output", help="Optional path for a signed offline verification result")
    args = parser.parse_args(argv)
    result = verify_artifact_set(args.root, args.key, args.report)
    if args.signed_output:
        inventory_digest = str(result.get("checks", {}).get("inventory", {}).get("inventory_digest", ""))
        signed = sign_verification_result(result, inventory_digest, inventory_digest, args.key)
        signed_path = Path(args.signed_output).resolve()
        signed_path.parent.mkdir(parents=True, exist_ok=True)
        signed_path.write_text(json.dumps(signed, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result["signed_result_path"] = str(signed_path)
        result["signed_result_digest"] = signed["result_digest"]
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("status") == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())

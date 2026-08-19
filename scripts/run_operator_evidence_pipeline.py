"""Run the bounded operator evidence pipeline without executing external lanes.

Patterns are adapted from the NOESIS readiness matrix, signed external evidence
aggregator, report bundle exporter, and operator-owned audit workflows. The
pipeline reads only supplied JSON artifacts and never launches executables,
providers, network requests, or child runtimes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.aggregate_external_evidence import aggregate_external_evidence
from scripts.chain_summary import build_chain_summary
from scripts.reproducibility_receipt import build_reproducibility_receipt
from scripts.artifact_inventory import build_inventory
from scripts.signed_verification_result import sign_verification_result
from scripts.verify_operator_artifact_set import verify_artifact_set
from scripts.export_operator_report import export_snapshot
from scripts.external_evidence_readiness import build_matrix
from scripts.release_readiness_snapshot import build_snapshot, verify_snapshot
from scripts.release_gate_artifact import build_gate_artifact
from scripts.signed_readiness_receipt import sign_readiness_receipt
from scripts.execution_conformance import build_conformance

SCHEMA = "noesis.operator-evidence-pipeline.v1"


def _read(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("json_object_required:" + path)
    return value


def run_pipeline(manifest_path: str, evidence_paths: list[str], key: str, output_dir: str, snapshot_path: str | None = None, report_output: str | None = None, readiness_snapshot_path: str | None = None, readiness_test_count: int | None = None, readiness_python_version: str | None = None, native_status: str = "not_run", external_status: str = "not_run", conformance_replay_path: str | None = None) -> dict[str, Any]:
    if not isinstance(key, str) or len(key.encode("utf-8")) < 16:
        raise ValueError("pipeline_signing_key_too_short")
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    manifest = _read(manifest_path)
    evidence = [_read(path) for path in evidence_paths]
    matrix = build_matrix(manifest, evidence, key)
    aggregate = aggregate_external_evidence(manifest, evidence, key)
    matrix_path = root / "external-evidence-readiness.json"
    aggregate_path = root / "signed-external-evidence-aggregate.json"
    matrix_path.write_text(json.dumps(matrix, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    aggregate_path.write_text(json.dumps(aggregate, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path = None
    if report_output:
        if not snapshot_path:
            raise ValueError("report_output_requires_snapshot")
        snapshot = _read(snapshot_path)
        export_snapshot(snapshot, report_output, key.encode("utf-8"), external_aggregate=aggregate)
        report_path = str(Path(report_output))
    artifact_paths = [matrix_path, aggregate_path]
    if report_path:
        artifact_paths.append(Path(report_path))
    inventory = build_inventory(root, artifact_paths, key, {"pipeline_schema": SCHEMA, "status": aggregate["overall_status"], "comparative_ready": bool(aggregate["comparative_ready"]), "required_lanes": list(aggregate["required_lanes"])})
    inventory_path = root / "artifact-manifest.json"
    inventory_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    verification = verify_artifact_set(root, key, report_path)
    signed_verification = sign_verification_result(verification, inventory["inventory_digest"], inventory["inventory_digest"], key)
    verification_path = root / "verification-result.json"
    verification_path.write_text(json.dumps(signed_verification, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    chain_summary = build_chain_summary(inventory, aggregate, signed_verification, key)
    chain_summary_path = root / "chain-summary.json"
    chain_summary_path.write_text(json.dumps(chain_summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    reproducibility = build_reproducibility_receipt(inventory["inventory_digest"], aggregate["aggregate_digest"], chain_summary["chain_digest"], key)
    reproducibility_path = root / "reproducibility-receipt.json"
    reproducibility_path.write_text(json.dumps(reproducibility, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    readiness_snapshot_file = None
    gate_artifact_file = None
    readiness_receipt_file = None
    conformance_file = None
    if readiness_test_count is not None or readiness_python_version is not None or readiness_snapshot_path:
        if readiness_test_count is None or readiness_python_version is None:
            raise ValueError("readiness_metadata_incomplete")
        if readiness_snapshot_path:
            readiness_snapshot = _read(readiness_snapshot_path)
        else:
            readiness_snapshot = build_snapshot({"status": aggregate["overall_status"]}, readiness_test_count, readiness_python_version, native_status, external_status)
        snapshot_check = verify_snapshot(readiness_snapshot)
        if snapshot_check.get("status") != "passed":
            raise ValueError("readiness_snapshot_invalid:" + str(snapshot_check.get("reason", "unknown")))
        readiness_snapshot_file = root / "release-readiness.json"
        readiness_snapshot_file.write_text(json.dumps(readiness_snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        gate_result = {"status": aggregate["overall_status"], "stages": {"post_transfer_audit": {"status": aggregate["overall_status"]}, "release_readiness_snapshot": {"status": readiness_snapshot["overall_status"]}}}
        gate_artifact = build_gate_artifact(gate_result)
        gate_artifact_file = root / "release-gate.json"
        gate_artifact_file.write_text(json.dumps(gate_artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        readiness_receipt = sign_readiness_receipt(readiness_snapshot, gate_artifact, readiness_test_count, readiness_python_version, key)
        readiness_receipt_file = root / "signed-readiness-receipt.json"
        readiness_receipt_file.write_text(json.dumps(readiness_receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        replay_result = _read(conformance_replay_path) if conformance_replay_path else {"status": "not_run"}
        conformance = build_conformance(readiness_snapshot, matrix, replay_result, gate_artifact)
        conformance_file = root / "execution-conformance.json"
        conformance_file.write_text(json.dumps(conformance, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    status = aggregate["overall_status"]
    lane_statuses = [str(value.get("status", "blocked")) for value in aggregate["lanes"].values()]
    status_counts = {name: lane_statuses.count(name) for name in ("passed", "not_run", "blocked", "unsupported")}
    return {
        "schema_version": SCHEMA,
        "status": status,
        "status_vocabulary": ["passed", "not_run", "blocked", "unsupported"],
        "status_counts": status_counts,
        "exit_code": 0 if status == "passed" else 2,
        "comparative_ready": bool(aggregate["comparative_ready"]),
        "matrix_status": matrix["overall_status"],
        "aggregate_status": aggregate["overall_status"],
        "artifacts": {"readiness_matrix": str(matrix_path), "signed_aggregate": str(aggregate_path), "report_bundle": report_path, "artifact_manifest": str(inventory_path), "verification_result": str(verification_path), "chain_summary": str(chain_summary_path), "reproducibility_receipt": str(reproducibility_path), "release_readiness": str(readiness_snapshot_file) if readiness_snapshot_file else None, "release_gate": str(gate_artifact_file) if gate_artifact_file else None, "signed_readiness_receipt": str(readiness_receipt_file) if readiness_receipt_file else None, "execution_conformance": str(conformance_file) if conformance_file else None},
        "verification_result_digest": signed_verification["result_digest"],
        "chain_summary_digest": chain_summary["chain_digest"],
        "reproducibility_receipt_digest": reproducibility["receipt_digest"],
        "artifact_manifest_digest": inventory["inventory_digest"],
        "required_lanes": list(aggregate["required_lanes"]),
        "external_execution_claim": False,
        "automatic_execution": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run bounded NOESIS external evidence pipeline")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--evidence", nargs="*", default=[])
    parser.add_argument("--key", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--snapshot")
    parser.add_argument("--report-output")
    parser.add_argument("--readiness-snapshot")
    parser.add_argument("--readiness-test-count", type=int)
    parser.add_argument("--readiness-python-version")
    parser.add_argument("--native-status", default="not_run")
    parser.add_argument("--external-status", default="not_run")
    parser.add_argument("--conformance-replay")
    args = parser.parse_args(argv)
    try:
        result = run_pipeline(args.manifest, args.evidence, args.key, args.output_dir, args.snapshot, args.report_output, args.readiness_snapshot, args.readiness_test_count, args.readiness_python_version, args.native_status, args.external_status, args.conformance_replay)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result["status"] == "passed" else 2
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"schema_version": SCHEMA, "status": "blocked", "reason": type(exc).__name__ + ":" + str(exc)[:160], "automatic_execution": False}, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

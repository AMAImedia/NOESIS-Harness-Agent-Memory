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
from scripts.artifact_inventory import build_inventory
from scripts.export_operator_report import export_snapshot
from scripts.external_evidence_readiness import build_matrix

SCHEMA = "noesis.operator-evidence-pipeline.v1"


def _read(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("json_object_required:" + path)
    return value


def run_pipeline(manifest_path: str, evidence_paths: list[str], key: str, output_dir: str, snapshot_path: str | None = None, report_output: str | None = None) -> dict[str, Any]:
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
        "artifacts": {"readiness_matrix": str(matrix_path), "signed_aggregate": str(aggregate_path), "report_bundle": report_path, "artifact_manifest": str(inventory_path)},
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
    args = parser.parse_args(argv)
    try:
        result = run_pipeline(args.manifest, args.evidence, args.key, args.output_dir, args.snapshot, args.report_output)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result["status"] == "passed" else 2
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"schema_version": SCHEMA, "status": "blocked", "reason": type(exc).__name__ + ":" + str(exc)[:160], "automatic_execution": False}, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

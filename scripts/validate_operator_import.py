"""Validate operator bundle compatibility before importing signed evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from scripts.build_comparative_report import build_report
from scripts.build_operator_case_bundle import SCHEMA as BUNDLE_SCHEMA, digest
from scripts.external_evidence_readiness import LANES

IMPORT_SCHEMA = "noesis.operator-import.v1"


def _bundle_body(bundle: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in bundle.items() if key != "bundle_digest"}


def validate_import(bundle: Mapping[str, Any], manifest: Mapping[str, Any], evidence: Sequence[Mapping[str, Any]], cases: Sequence[Mapping[str, Any]], key: str) -> dict[str, Any]:
    errors: list[str] = []
    if bundle.get("schema_version") != BUNDLE_SCHEMA:
        errors.append("bundle_schema_mismatch")
    if bundle.get("mode") != "readiness_only":
        errors.append("bundle_mode_mismatch")
    if bundle.get("execution_allowed") is not False or bundle.get("automatic_execution") is not False:
        errors.append("execution_boundary_violation")
    if bundle.get("bundle_digest") != digest(_bundle_body(bundle)):
        errors.append("bundle_digest_mismatch")
    if bundle.get("manifest_digest") != digest(manifest):
        errors.append("manifest_drift")
    manifest_cases = [str(item) for item in manifest.get("case_ids", ())] if isinstance(manifest.get("case_ids"), Sequence) and not isinstance(manifest.get("case_ids"), (str, bytes)) else []
    if list(bundle.get("case_ids", ())) != manifest_cases:
        errors.append("case_manifest_drift")
    if list(bundle.get("required_lanes", ())) != list(LANES):
        errors.append("lane_set_drift")
    revisions = manifest.get("revisions") if isinstance(manifest.get("revisions"), Mapping) else {}
    for record in evidence:
        lane = record.get("system")
        if lane in LANES and revisions.get(lane) and record.get("revision") != revisions.get(lane):
            errors.append("lane_revision_drift:%s" % lane)
        if lane in LANES and manifest.get("protocol_fingerprint") and record.get("protocol_fingerprint") != manifest.get("protocol_fingerprint"):
            errors.append("lane_protocol_drift:%s" % lane)
    report = build_report(manifest, evidence, key, cases) if not errors else {"score_status": "blocked", "score_claim": False, "score_available": False, "case_errors": []}
    status = "blocked" if errors else ("accepted" if report.get("score_status") == "available" else "accepted_not_run")
    return {
        "schema_version": IMPORT_SCHEMA,
        "status": status,
        "errors": sorted(set(errors)),
        "report": report,
        "external_execution_claim": False,
        "score_claim": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate operator bundle and import signed evidence")
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--evidence", nargs="*", default=[])
    parser.add_argument("--cases", nargs="*", default=[])
    parser.add_argument("--key", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    evidence = [json.loads(Path(path).read_text(encoding="utf-8")) for path in args.evidence]
    cases = [json.loads(Path(path).read_text(encoding="utf-8")) for path in args.cases]
    result = validate_import(bundle, manifest, evidence, cases, args.key)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": args.output, "status": result["status"], "score_claim": False}, ensure_ascii=False))
    return 0 if result["status"] != "blocked" else 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build a fail-closed readiness matrix for pinned external evidence lanes."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from scripts.ingest_runner_result import receipt_id, verify_evidence
from scripts.external_runner_contract import REQUIRED_SYSTEMS

SCHEMA = "noesis.external-evidence-readiness.v1"
LANES = ("hermes", "opencode", "deepseek_harness")
READINESS = frozenset({"passed", "not_run", "blocked", "unsupported"})


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _as_records(values: Sequence[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    result: dict[str, list[Mapping[str, Any]]] = {lane: [] for lane in LANES}
    for value in values:
        system = value.get("system")
        if isinstance(system, str):
            result.setdefault(system, []).append(value)
    return result


def build_matrix(manifest: Mapping[str, Any], evidence: Sequence[Mapping[str, Any]], key: str) -> dict[str, Any]:
    revisions = manifest.get("revisions") if isinstance(manifest.get("revisions"), Mapping) else {}
    expected_environment = manifest.get("environment_digests") if isinstance(manifest.get("environment_digests"), Mapping) else {}
    expected_fingerprint = str(manifest.get("protocol_fingerprint", ""))
    grouped = _as_records(evidence)
    lanes: dict[str, dict[str, Any]] = {}
    accepted_fingerprints: set[str] = set()
    for lane in LANES:
        revision = str(revisions.get(lane, ""))
        records = grouped.get(lane, [])
        checks: list[str] = []
        if not revision:
            lanes[lane] = {"status": "not_run", "reason": "missing_exact_revision", "checks": ["revision_missing"]}
            continue
        if len(records) > 1:
            lanes[lane] = {"status": "blocked", "reason": "duplicate_system_record", "checks": ["duplicate_system_record"]}
            continue
        if not records:
            lanes[lane] = {"status": "blocked", "reason": "evidence_missing_for_pinned_revision", "checks": ["evidence_missing"]}
            continue
        record = records[0]
        if record.get("revision") != revision:
            checks.append("revision_mismatch")
        if expected_environment.get(lane) and record.get("environment_digest") != expected_environment.get(lane):
            checks.append("environment_digest_mismatch")
        if not verify_evidence(record, key):
            checks.append("signature_or_envelope_invalid")
        if record.get("receipt_id") != receipt_id(record):
            checks.append("stale_or_mismatched_receipt")
        status = str(record.get("status", "not_run"))
        if status == "unsupported":
            checks.append("lane_unsupported")
        if status == "not_run":
            checks.append("execution_not_run")
        fingerprint = record.get("protocol_fingerprint")
        if isinstance(fingerprint, str):
            accepted_fingerprints.add(fingerprint)
        if checks:
            if "lane_unsupported" in checks and len(checks) == 1:
                lane_status = "unsupported"
            elif checks == ["execution_not_run"]:
                lane_status = "not_run"
            else:
                lane_status = "blocked"
        else:
            lane_status = "passed"
        lanes[lane] = {"status": lane_status, "reason": ";".join(checks) if checks else "accepted_signed_evidence", "checks": checks, "revision": record.get("revision"), "receipt_id": record.get("receipt_id")}
    comparable = len(accepted_fingerprints) == 1 and sum(item["status"] == "passed" for item in lanes.values()) >= 2
    global_checks: list[str] = []
    if expected_fingerprint and accepted_fingerprints and accepted_fingerprints != {expected_fingerprint}:
        global_checks.append("protocol_fingerprint_mismatch")
    if len(accepted_fingerprints) > 1:
        global_checks.append("protocol_fingerprint_conflict")
    if not comparable:
        global_checks.append("comparative_readiness_not_met")
    lane_statuses = [item["status"] for item in lanes.values()]
    if comparable and not global_checks:
        overall = "passed"
    elif any(status == "blocked" for status in lane_statuses) or "protocol_fingerprint_conflict" in global_checks or "protocol_fingerprint_mismatch" in global_checks:
        overall = "blocked"
    elif lane_statuses and all(status == "unsupported" for status in lane_statuses):
        overall = "unsupported"
    else:
        overall = "not_run"
    return {
        "schema_version": SCHEMA,
        "readiness_vocabulary": sorted(READINESS),
        "required_lanes": list(LANES),
        "lanes": lanes,
        "overall_status": overall,
        "comparative_ready": comparable and not global_checks,
        "global_checks": global_checks,
        "evidence_count": len(evidence),
        "matrix_digest": _digest({"lanes": lanes, "global_checks": global_checks}),
        "execution_claim": "not_run" if not evidence else "evidence_ingestion_only",
        "native_or_external_execution_claim": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build fail-closed external evidence readiness matrix")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--evidence", nargs="*", default=[])
    parser.add_argument("--key", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    evidence = [json.loads(Path(path).read_text(encoding="utf-8")) for path in args.evidence]
    report = build_matrix(manifest, evidence, args.key)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": args.output, "overall_status": report["overall_status"], "comparative_ready": report["comparative_ready"]}, ensure_ascii=False))
    return 0 if report["overall_status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())

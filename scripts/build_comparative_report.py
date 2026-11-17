"""Build a fail-closed comparative report from signed external evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from scripts.external_evidence_readiness import LANES, build_matrix
from scripts.ingest_runner_result import verify_evidence

SCHEMA = "noesis.comparative-report.v1"
PROTOCOL_SCHEMA = "noesis.independent-comparative-scoring.v1"
CASE_SCHEMA = "noesis.comparative-case-receipt.v1"
DIMENSIONS = ("task_correctness", "patch_correctness", "recovery", "isolation_egress", "cross_agent_leakage", "long_context_use", "review_burden")
MANDATORY_SAFETY_FAILURES = frozenset({"approval_bypass", "credential_leakage", "cross_agent_leakage", "unauthorized_network_access", "unauthorized_filesystem_access", "receipt_integrity_failure"})


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def case_receipt_id(receipt: Mapping[str, Any]) -> str:
    basis = {name: receipt.get(name) for name in ("system", "revision", "protocol_fingerprint", "case_id", "case_digest", "evaluator_revision")}
    return _digest(basis)


def case_signature(receipt: Mapping[str, Any], key: str) -> str:
    if not key or len(key) < 16:
        raise ValueError("case signing key must be at least 16 characters")
    import hmac
    return "hmac-sha256:" + hmac.new(key.encode("utf-8"), _canonical(receipt), hashlib.sha256).hexdigest()


def create_case_receipt(*, system: str, revision: str, protocol_fingerprint: str, case_id: str, evaluator_revision: str, dimensions: Mapping[str, Any], safety_failures: Sequence[str] = (), case_digest: str = "", key: str) -> dict[str, Any]:
    safe_dimensions = json.loads(json.dumps(dict(dimensions), ensure_ascii=False, sort_keys=True))
    unsigned = {"schema_version": CASE_SCHEMA, "system": system, "revision": revision, "protocol_fingerprint": protocol_fingerprint, "case_id": case_id, "case_digest": case_digest or _digest({"case_id": case_id, "dimensions": safe_dimensions}), "evaluator_revision": evaluator_revision, "dimensions": safe_dimensions, "safety_failures": sorted({str(item) for item in safety_failures})}
    unsigned["receipt_id"] = case_receipt_id(unsigned)
    return {**unsigned, "signature": case_signature(unsigned, key)}


def verify_case_receipt(receipt: Mapping[str, Any], key: str) -> bool:
    if not isinstance(receipt, Mapping) or receipt.get("schema_version") != CASE_SCHEMA:
        return False
    if receipt.get("receipt_id") != case_receipt_id(receipt):
        return False
    dimensions = receipt.get("dimensions")
    failures = receipt.get("safety_failures")
    if not isinstance(dimensions, Mapping) or not isinstance(failures, list):
        return False
    if set(dimensions) != set(DIMENSIONS) or any(name not in DIMENSIONS or not isinstance(value, Mapping) or value.get("status") != "observed" or not isinstance(value.get("value"), (int, float)) or isinstance(value.get("value"), bool) or not 0.0 <= float(value.get("value")) <= 1.0 for name, value in dimensions.items()):
        return False
    try:
        supplied = str(receipt.get("signature", ""))
        expected = case_signature({name: value for name, value in receipt.items() if name != "signature"}, key)
    except (TypeError, ValueError, UnicodeError):
        return False
    import hmac
    return hmac.compare_digest(supplied, expected)


def _bounded_metric_view(evidence: Mapping[str, Any]) -> dict[str, Any]:
    metrics = evidence.get("metrics")
    if not isinstance(metrics, Mapping):
        return {}
    result: dict[str, Any] = {}
    for name, record in list(metrics.items())[:32]:
        if not isinstance(name, str) or not isinstance(record, Mapping):
            continue
        item = {"status": str(record.get("status", "not_run"))}
        if isinstance(record.get("value"), (int, float)) and not isinstance(record.get("value"), bool):
            item["value"] = float(record["value"])
        if isinstance(record.get("reason"), str):
            item["reason"] = record["reason"][:256]
        result[name[:128]] = item
    return result


def _aggregate_cases(cases: Sequence[Mapping[str, Any]], expected_case_ids: Sequence[str], lane_identities: Mapping[str, Mapping[str, Any]], key: str) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    seen: set[tuple[str, str]] = set()
    valid: list[Mapping[str, Any]] = []
    expected = tuple(dict.fromkeys(str(item) for item in expected_case_ids))
    for case in cases:
        identity = (str(case.get("system", "")), str(case.get("case_id", "")))
        if identity in seen:
            errors.append("duplicate_case:%s:%s" % identity)
            continue
        seen.add(identity)
        if not verify_case_receipt(case, key):
            errors.append("invalid_case_receipt:%s:%s" % identity)
            continue
        lane_identity = lane_identities.get(str(case.get("system")), {})
        if lane_identity and (case.get("revision") != lane_identity.get("revision") or case.get("protocol_fingerprint") != lane_identity.get("protocol_fingerprint")):
            errors.append("case_identity_mismatch:%s:%s" % identity)
            continue
        valid.append(case)
    grouped: dict[str, list[Mapping[str, Any]]] = {lane: [] for lane in LANES}
    for case in valid:
        if case.get("system") in grouped:
            grouped[str(case["system"])].append(case)
    if expected:
        for lane in LANES:
            missing = sorted(set(expected) - {str(item.get("case_id")) for item in grouped[lane]})
            errors.extend("missing_case:%s:%s" % (lane, case_id) for case_id in missing)
    aggregates: dict[str, Any] = {}
    for lane in LANES:
        lane_cases = grouped[lane]
        failures = sorted({str(flag) for case in lane_cases for flag in case.get("safety_failures", [])})
        values: dict[str, float] = {}
        for dimension in DIMENSIONS:
            observations = [case.get("dimensions", {}).get(dimension, {}).get("value") for case in lane_cases if isinstance(case.get("dimensions", {}).get(dimension), Mapping)]
            numeric = [float(value) for value in observations if isinstance(value, (int, float)) and not isinstance(value, bool) and 0.0 <= float(value) <= 1.0]
            if numeric:
                values[dimension] = sum(numeric) / len(numeric)
        aggregates[lane] = {"case_count": len(lane_cases), "dimension_means": values, "safety_failures": failures, "safety_clean": not bool(set(failures) & MANDATORY_SAFETY_FAILURES)}
    return aggregates, sorted(set(errors))


def build_report(manifest: Mapping[str, Any], evidence: Sequence[Mapping[str, Any]], key: str, cases: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    readiness = build_matrix(manifest, evidence, key)
    grouped = {lane: [] for lane in LANES}
    for record in evidence:
        system = record.get("system")
        if system in grouped:
            grouped[system].append(record)
    lanes: dict[str, dict[str, Any]] = {}
    for lane in LANES:
        readiness_lane = readiness["lanes"][lane]
        record = grouped[lane][0] if len(grouped[lane]) == 1 else None
        lanes[lane] = {
            "status": readiness_lane["status"],
            "reason": readiness_lane["reason"],
            "revision": readiness_lane.get("revision", record.get("revision") if record else None),
            "receipt_id": readiness_lane.get("receipt_id", record.get("receipt_id") if record else None),
            "signed_evidence_verified": bool(record is not None and verify_evidence(record, key)),
            "metric_view": _bounded_metric_view(record) if record is not None else {},
            "score": None,
            "score_status": "not_run" if readiness_lane["status"] == "not_run" else "blocked",
        }
        if readiness_lane["status"] == "passed":
            lanes[lane]["score_status"] = "not_run"
            lanes[lane]["reason"] = "accepted_evidence_requires_case_level_scoring"
    expected_case_ids = manifest.get("case_ids", ()) if isinstance(manifest.get("case_ids", ()), Sequence) and not isinstance(manifest.get("case_ids"), (str, bytes)) else ()
    lane_identities = {lane: {"revision": grouped[lane][0].get("revision"), "protocol_fingerprint": grouped[lane][0].get("protocol_fingerprint")} for lane in LANES if len(grouped[lane]) == 1}
    aggregates, case_errors = _aggregate_cases(cases, expected_case_ids, lane_identities, key)
    ready = bool(readiness.get("comparative_ready"))
    complete_cases = bool(cases) and not case_errors and all(aggregates[lane]["case_count"] == len(tuple(expected_case_ids)) for lane in LANES) if expected_case_ids else False
    safety_clean = complete_cases and all(aggregates[lane]["safety_clean"] for lane in LANES)
    score_available = ready and complete_cases and safety_clean
    cross_lane_means: dict[str, float] = {}
    if score_available:
        for dimension in DIMENSIONS:
            values = [aggregates[lane]["dimension_means"][dimension] for lane in LANES if dimension in aggregates[lane]["dimension_means"]]
            if len(values) == len(LANES):
                cross_lane_means[dimension] = sum(values) / len(values)
    return {
        "schema_version": SCHEMA,
        "protocol_schema": PROTOCOL_SCHEMA,
        "readiness": readiness,
        "lanes": lanes,
        "case_aggregates": aggregates,
        "case_errors": case_errors,
        "case_count": len(cases),
        "cross_lane_dimension_means": cross_lane_means,
        "score_available": score_available,
        "score_status": "available" if score_available else ("blocked" if case_errors or not safety_clean and cases else "not_run"),
        "score_claim": False,
        "reason": "external_execution_not_ready" if not ready else ("case_level_scoring_not_ingested" if not cases else ("case_corpus_incomplete_or_invalid" if not complete_cases else ("mandatory_safety_failure" if not safety_clean else "case_level_scoring_available_for_review"))),
        "report_digest": _digest({"readiness": readiness, "lanes": lanes}),
        "native_or_external_execution_claim": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a fail-closed signed-evidence comparative report")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--evidence", nargs="*", default=[])
    parser.add_argument("--cases", nargs="*", default=[])
    parser.add_argument("--key", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    evidence = [json.loads(Path(path).read_text(encoding="utf-8")) for path in args.evidence]
    cases = [json.loads(Path(path).read_text(encoding="utf-8")) for path in args.cases]
    report = build_report(manifest, evidence, args.key, cases)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": args.output, "score_status": report["score_status"], "score_claim": report["score_claim"]}, ensure_ascii=False))
    return 0 if report["score_claim"] is False else 2


if __name__ == "__main__":
    raise SystemExit(main())

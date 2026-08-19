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


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


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


def build_report(manifest: Mapping[str, Any], evidence: Sequence[Mapping[str, Any]], key: str) -> dict[str, Any]:
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
    ready = bool(readiness.get("comparative_ready"))
    return {
        "schema_version": SCHEMA,
        "protocol_schema": PROTOCOL_SCHEMA,
        "readiness": readiness,
        "lanes": lanes,
        "score_available": False,
        "score_status": "not_run" if not ready else "not_run",
        "score_claim": False,
        "reason": "external_execution_not_ready" if not ready else "case_level_scoring_not_ingested",
        "report_digest": _digest({"readiness": readiness, "lanes": lanes}),
        "native_or_external_execution_claim": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a fail-closed signed-evidence comparative report")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--evidence", nargs="*", default=[])
    parser.add_argument("--key", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    evidence = [json.loads(Path(path).read_text(encoding="utf-8")) for path in args.evidence]
    report = build_report(manifest, evidence, args.key)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": args.output, "score_status": report["score_status"], "score_claim": report["score_claim"]}, ensure_ascii=False))
    return 0 if report["score_claim"] is False else 2


if __name__ == "__main__":
    raise SystemExit(main())

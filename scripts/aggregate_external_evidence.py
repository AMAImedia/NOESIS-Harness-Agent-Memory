"""Aggregate signed external-lane evidence without executing external systems.

Patterns are adapted from the existing NOESIS readiness verifier, signed report
bundles, Hermes/OpenCode/DeepSeek lane contracts, and operator-owned evidence
receipts. This module only verifies and aggregates data; it never launches an
executable, provider, network request, or child runtime.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from scripts.external_evidence_readiness import LANES, build_matrix

SCHEMA = "noesis.signed-external-evidence-aggregate.v1"


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def aggregate_external_evidence(manifest: Mapping[str, Any], evidence: Sequence[Mapping[str, Any]], key: str) -> dict[str, Any]:
    """Return a deterministic signed aggregate; fail closed on invalid inputs."""
    if not isinstance(manifest, Mapping) or not isinstance(evidence, Sequence) or isinstance(evidence, (str, bytes)):
        raise ValueError("aggregate_input_invalid")
    if not isinstance(key, str) or len(key.encode("utf-8")) < 16:
        raise ValueError("aggregate_signing_key_too_short")
    ordered_evidence = sorted((dict(item) for item in evidence), key=lambda item: (str(item.get("system", "")), str(item.get("revision", "")), str(item.get("receipt_id", "")), _digest(item)))
    matrix = build_matrix(manifest, ordered_evidence, key)
    lanes = {lane: dict(matrix["lanes"].get(lane, {"status": "blocked", "reason": "lane_missing", "checks": ["lane_missing"]})) for lane in LANES}
    unsigned = {
        "schema_version": SCHEMA,
        "matrix_schema_version": matrix["schema_version"],
        "manifest_digest": _digest(manifest),
        "evidence_digest": _digest(ordered_evidence),
        "matrix_digest": matrix["matrix_digest"],
        "required_lanes": list(LANES),
        "lanes": lanes,
        "overall_status": matrix["overall_status"],
        "comparative_ready": bool(matrix["comparative_ready"]),
        "global_checks": list(matrix["global_checks"]),
        "evidence_count": int(matrix["evidence_count"]),
        "native_or_external_execution_claim": False,
        "execution_claim": matrix["execution_claim"],
        "claim_boundary": "signed_evidence_aggregation_only",
    }
    return {**unsigned, "aggregate_digest": _digest(unsigned), "signature": hmac.new(key.encode("utf-8"), _canonical(unsigned), hashlib.sha256).hexdigest()}


def verify_aggregate(value: Mapping[str, Any], key: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or value.get("schema_version") != SCHEMA:
        return {"status": "blocked", "reason": "aggregate_schema_invalid"}
    if not isinstance(key, str) or len(key.encode("utf-8")) < 16:
        return {"status": "blocked", "reason": "aggregate_signing_key_too_short"}
    unsigned = {k: value[k] for k in value if k not in {"aggregate_digest", "signature"}}
    if value.get("aggregate_digest") != _digest(unsigned):
        return {"status": "blocked", "reason": "aggregate_digest_mismatch"}
    expected = hmac.new(key.encode("utf-8"), _canonical(unsigned), hashlib.sha256).hexdigest()
    if not isinstance(value.get("signature"), str) or not hmac.compare_digest(value["signature"], expected):
        return {"status": "blocked", "reason": "aggregate_signature_invalid"}
    lanes = value.get("lanes")
    if list(value.get("required_lanes", ())) != list(LANES) or not isinstance(lanes, Mapping):
        return {"status": "blocked", "reason": "aggregate_lane_identity_invalid"}
    if value.get("native_or_external_execution_claim") is not False or value.get("claim_boundary") != "signed_evidence_aggregation_only":
        return {"status": "blocked", "reason": "aggregate_claim_boundary_invalid"}
    return {"status": "passed", "comparative_ready": bool(value.get("comparative_ready")), "aggregate_digest": str(value["aggregate_digest"])}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aggregate verified external evidence without launching external lanes")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--evidence", nargs="*", default=[])
    parser.add_argument("--key", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        evidence = [json.loads(Path(path).read_text(encoding="utf-8")) for path in args.evidence]
        result = aggregate_external_evidence(manifest, evidence, args.key)
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"output": args.output, "overall_status": result["overall_status"], "comparative_ready": result["comparative_ready"]}, ensure_ascii=False, sort_keys=True))
        return 0 if result["overall_status"] == "passed" else 2
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "blocked", "reason": type(exc).__name__ + ":" + str(exc)[:160]}, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

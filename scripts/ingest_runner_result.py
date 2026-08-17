#!/usr/bin/env python3
"""Validate external runner output and create a private signed evidence record.

The key is supplied at runtime and is never written to the evidence document.
This is an integrity/authenticity envelope for a controlled operator workflow,
not a replacement for a public-key release signature.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import re
from pathlib import Path
from typing import Any, Mapping

from scripts.external_runner_contract import ALLOWED_STATUS, REQUIRED_FIELDS, validate_result

SCHEMA = "noesis.runner-evidence.v1"
METRIC_STATUS = ALLOWED_STATUS | {"observed"}
_CREDENTIAL_PATTERNS = (
    re.compile(r"(?i)\b(?:api[_-]?key|token|password|secret)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"\b(?:sk|hf|ghp|github_pat)_[A-Za-z0-9_\-]{12,}\b"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{12,}"),
)


def canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str) + "\n").encode("utf-8")


def signature(payload: Mapping[str, Any], key: str) -> str:
    if not key or len(key) < 16:
        raise ValueError("evidence signing key must be at least 16 characters")
    return "hmac-sha256:" + hmac.new(key.encode("utf-8"), canonical(payload), hashlib.sha256).hexdigest()


def contains_credential_like(value: Any) -> bool:
    if isinstance(value, str):
        return any(pattern.search(value) for pattern in _CREDENTIAL_PATTERNS)
    if isinstance(value, Mapping):
        return any(contains_credential_like(key) or contains_credential_like(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return any(contains_credential_like(item) for item in value)
    return False


def ingest(spec: Mapping[str, Any], result: Mapping[str, Any], key: str) -> dict:
    errors = []
    valid_result, result_errors = validate_result(result)
    errors.extend(result_errors)
    if spec.get("schema_version") != "noesis.external-runner.v1":
        errors.append("invalid:spec_schema")
    for field in ("system", "revision", "model_provider", "task_manifest_sha256", "protocol_fingerprint"):
        if spec.get(field) != result.get(field):
            errors.append("identity_mismatch:" + field)
    if spec.get("workspace") != result.get("workspace"):
        errors.append("workspace_mismatch")
    if spec.get("argv") != result.get("argv"):
        errors.append("argv_mismatch")
    metrics = result.get("metrics")
    if not isinstance(metrics, Mapping) or not metrics:
        errors.append("metrics_required")
    else:
        for name, record in metrics.items():
            if not isinstance(name, str) or not isinstance(record, Mapping) or record.get("status") not in METRIC_STATUS:
                errors.append("invalid:metric:" + str(name))
    if contains_credential_like(result):
        errors.append("credential_like_content")
    accepted = not errors
    unsigned = {
        "schema_version": SCHEMA,
        "accepted": accepted,
        "errors": sorted(set(errors)),
        "system": result.get("system"),
        "revision": result.get("revision"),
        "task_manifest_sha256": result.get("task_manifest_sha256"),
        "model_provider": result.get("model_provider"),
        "protocol_fingerprint": result.get("protocol_fingerprint"),
        "workspace": result.get("workspace"),
        "status": result.get("status", "not_run"),
        "metrics": result.get("metrics", {}),
        "source_result_sha256": hashlib.sha256(canonical(result)).hexdigest(),
    }
    return {**unsigned, "signature": signature(unsigned, key)}


def verify_evidence(evidence: Mapping[str, Any], key: str) -> bool:
    signed = {name: value for name, value in evidence.items() if name != "signature"}
    supplied = str(evidence.get("signature", ""))
    return hmac.compare_digest(supplied, signature(signed, key)) and evidence.get("schema_version") == SCHEMA and evidence.get("accepted") is True


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Ingest and sign a pinned external runner result")
    parser.add_argument("--spec", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--key", required=True, help="runtime HMAC key; never persisted")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    result = json.loads(Path(args.result).read_text(encoding="utf-8"))
    evidence = ingest(spec, result, args.key)
    Path(args.output).write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": args.output, "accepted": evidence["accepted"], "errors": evidence["errors"]}, ensure_ascii=False))
    return 0 if evidence["accepted"] and verify_evidence(evidence, args.key) else 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Create a deterministic, readiness-only operator bundle for external case runs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from scripts.external_evidence_readiness import LANES

SCHEMA = "noesis.operator-case-bundle.v1"


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def validate_manifest(manifest: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema_version") not in (None, "noesis.external-runner-manifest.v1"):
        errors.append("invalid_manifest_schema")
    revisions = manifest.get("revisions")
    if not isinstance(revisions, Mapping):
        errors.append("revisions_required")
    else:
        for lane in LANES:
            if revisions.get(lane) is not None and not isinstance(revisions.get(lane), str):
                errors.append("invalid_revision:%s" % lane)
    case_ids = manifest.get("case_ids")
    if not isinstance(case_ids, Sequence) or isinstance(case_ids, (str, bytes)) or not case_ids:
        errors.append("case_ids_required")
    else:
        normalized = [str(item) for item in case_ids]
        if any(not item for item in normalized):
            errors.append("empty_case_id")
        if len(set(normalized)) != len(normalized):
            errors.append("duplicate_case_id")
    if manifest.get("network_policy", "deny") != "deny":
        errors.append("network_must_be_deny")
    if manifest.get("credentials", "absent") != "absent":
        errors.append("credentials_must_be_absent")
    if manifest.get("workspace_mode", "disposable") != "disposable":
        errors.append("workspace_must_be_disposable")
    if not isinstance(manifest.get("protocol_fingerprint", ""), str) or len(manifest.get("protocol_fingerprint", "")) != 64:
        errors.append("protocol_fingerprint_required")
    return sorted(set(errors))


def build_bundle(manifest: Mapping[str, Any]) -> dict[str, Any]:
    errors = validate_manifest(manifest)
    revisions = manifest.get("revisions") if isinstance(manifest.get("revisions"), Mapping) else {}
    case_ids = [str(item) for item in manifest.get("case_ids", ())] if isinstance(manifest.get("case_ids"), Sequence) and not isinstance(manifest.get("case_ids"), (str, bytes)) else []
    lane_status = {lane: ("not_run" if not revisions.get(lane) else "ready_for_operator_preflight") for lane in LANES}
    status = "blocked" if errors else ("not_run" if any(value == "not_run" for value in lane_status.values()) else "ready_for_operator_preflight")
    payload = {
        "schema_version": SCHEMA,
        "mode": "readiness_only",
        "execution_allowed": False,
        "automatic_execution": False,
        "approval_required": True,
        "manifest_digest": digest(manifest),
        "case_ids": case_ids,
        "required_lanes": list(LANES),
        "lane_status": lane_status,
        "status": status,
        "errors": errors,
        "operator_steps": ["verify_manifest_digest", "verify_pinned_executable_and_environment", "obtain_explicit_approval", "run_provider_neutral_lane_command", "ingest_signed_receipt", "build_comparative_report"],
        "external_execution_claim": False,
    }
    payload["bundle_digest"] = digest(payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build readiness-only operator case bundle")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    bundle = build_bundle(manifest)
    Path(args.output).write_text(json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": args.output, "status": bundle["status"], "execution_allowed": bundle["execution_allowed"]}, ensure_ascii=False))
    return 0 if bundle["status"] != "blocked" else 2


if __name__ == "__main__":
    raise SystemExit(main())

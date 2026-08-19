"""Deterministic signed report bundle export.

Patterns adapted from the portable artifact audit, operator case bundles,
signed evidence aggregation, and fail-closed external readiness reports. The
bundle is an export only: it never executes lanes or upgrades claims.
"""
from __future__ import annotations

import hashlib
import hmac
import io
import json
import zipfile
from pathlib import Path
from typing import Any, Mapping

SCHEMA_VERSION = "noesis.signed-report-bundle.v1"
SCHEMA_VERSION_WITH_RECEIPTS = "noesis.signed-report-bundle.v2"
DOMAINS = ("local_execution", "native_parity", "external_comparative")
RECEIPT_DOMAIN = "lifecycle_receipt_audit"
DOMAINS_WITH_RECEIPTS = DOMAINS + (RECEIPT_DOMAIN,)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _signature(value: Mapping[str, Any], key: bytes) -> str:
    if not isinstance(key, bytes) or len(key) < 16:
        raise ValueError("signing_key_too_short")
    return hmac.new(key, _canonical(value), hashlib.sha256).hexdigest()


def build_report_bundle(output: str | Path, *, local_execution: Mapping[str, Any], native_parity: Mapping[str, Any], external_comparative: Mapping[str, Any], signing_key: bytes, lifecycle_receipt_audit: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
    domains = {"local_execution": dict(local_execution), "native_parity": dict(native_parity), "external_comparative": dict(external_comparative)}
    include_receipts = lifecycle_receipt_audit is not None
    if include_receipts:
        receipt_domain = dict(lifecycle_receipt_audit)
        receipt_domain.update({"claim": False, "execution_claim": False, "comparative_claim": False, "execution_lane_satisfied": False, "native_lane_satisfied": False, "external_lane_satisfied": False, "claim_boundary": "lifecycle_receipt_audit_only"})
        domains[RECEIPT_DOMAIN] = receipt_domain
    domain_names = DOMAINS_WITH_RECEIPTS if include_receipts else DOMAINS
    schema_version = SCHEMA_VERSION_WITH_RECEIPTS if include_receipts else SCHEMA_VERSION
    manifest = {"schema_version": schema_version, "domains": domain_names, "domain_digests": {name: _digest(domains[name]) for name in domain_names}, "claim_boundary": "export_only_no_execution_no_claim_escalation"}
    manifest["bundle_digest"] = _digest(manifest)
    signature = _signature(manifest, signing_key)
    files = {"manifest.json": manifest, "signature.json": {"schema_version": "noesis.signed-report-bundle-signature.v1", "bundle_digest": manifest["bundle_digest"], "signature": signature}}
    files.update({name + ".json": domains[name] for name in domain_names})
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o600 << 16
            archive.writestr(info, json.dumps(files[name], sort_keys=True, ensure_ascii=False, indent=2) + "\n")
    return {"schema_version": schema_version, "bundle_digest": manifest["bundle_digest"], "signature": signature, "output": str(output_path), "domains": list(domain_names), "claim_boundary": manifest["claim_boundary"]}


def verify_report_bundle(bundle: str | Path, signing_key: bytes) -> Mapping[str, Any]:
    try:
        with zipfile.ZipFile(bundle, "r") as archive:
            names = tuple(sorted(archive.namelist()))
            manifest_preview = json.loads(archive.read("manifest.json").decode("utf-8"))
            preview_domains = tuple(manifest_preview.get("domains", ()))
            expected = tuple(sorted(("manifest.json", "signature.json") + tuple(name + ".json" for name in preview_domains)))
            if names != expected:
                return {"status": "blocked", "reason": "bundle_file_set_mismatch", "claim": False}
            data = {name: json.loads(archive.read(name).decode("utf-8")) for name in names}
    except (OSError, zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError):
        return {"status": "blocked", "reason": "bundle_malformed", "claim": False}
    manifest = data["manifest.json"]
    manifest_domains = tuple(manifest.get("domains", ()))
    valid_schema = (manifest.get("schema_version") == SCHEMA_VERSION and manifest_domains == DOMAINS) or (manifest.get("schema_version") == SCHEMA_VERSION_WITH_RECEIPTS and manifest_domains == DOMAINS_WITH_RECEIPTS)
    if not valid_schema:
        return {"status": "blocked", "reason": "manifest_schema_or_domain_mismatch", "claim": False}
    unsigned = dict(manifest)
    bundle_digest = unsigned.pop("bundle_digest", "")
    if _digest(unsigned) != bundle_digest:
        return {"status": "blocked", "reason": "bundle_digest_mismatch", "claim": False}
    signature_record = data["signature.json"]
    if signature_record.get("bundle_digest") != bundle_digest or not hmac.compare_digest(str(signature_record.get("signature", "")), _signature(manifest, signing_key)):
        return {"status": "blocked", "reason": "bundle_signature_invalid", "claim": False}
    for domain in manifest_domains:
        if manifest["domain_digests"].get(domain) != _digest(data[domain + ".json"]):
            return {"status": "blocked", "reason": "domain_digest_mismatch:" + domain, "claim": False}
    if RECEIPT_DOMAIN in manifest_domains:
        receipt_domain = data[RECEIPT_DOMAIN + ".json"]
        if any(receipt_domain.get(field) is not False for field in ("claim", "execution_claim", "comparative_claim", "execution_lane_satisfied", "native_lane_satisfied", "external_lane_satisfied")):
            return {"status": "blocked", "reason": "receipt_domain_claim_escalation", "claim": False}
    return {"status": "passed", "reason": "deterministic_signed_report_bundle_verified", "bundle_digest": bundle_digest, "domains": list(manifest_domains), "claim": False, "claim_boundary": "export_verification_only"}


__all__ = ["SCHEMA_VERSION", "SCHEMA_VERSION_WITH_RECEIPTS", "DOMAINS", "RECEIPT_DOMAIN", "DOMAINS_WITH_RECEIPTS", "build_report_bundle", "verify_report_bundle"]

"""Fail-closed projection of committed local evidence for the operator plane.

Patterns adapted from agentmemory fail-closed status surfaces, signed report
bundle canonical-JSON digest verification (report_bundle and
lifecycle_audit_ingestion), and the HealthServer bounded provider snapshot
convention (evidence_aggregate). Deterministic only: no LLM, no network,
no wall clock; a missing or corrupt document degrades to an unavailable
status instead of raising.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Any, List, Mapping

EVIDENCE_PROJECTION_SCHEMA = "noesis.evidence-projection.v1"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _read_json_object(path) -> Any:
    with open(Path(path), "rb") as handle:
        raw = handle.read()
    return json.loads(raw.decode("utf-8"))


def _unavailable(reason: str) -> Mapping[str, Any]:
    return {"schema_version": "", "available": False, "digest_verified": False, "output_digest": "", "reason": reason}


def load_workload_evidence(path) -> Mapping[str, Any]:
    """Load docs/MULTI_AGENT_WORKLOAD_EVIDENCE.json and verify its output_digest.

    digest_verified recomputes sha256 over canonical JSON (sort_keys, compact
    separators) of the payload minus the output_digest key and compares it to
    the stored value. Missing or corrupt files fail closed with available
    False; this function never raises.
    """
    if path is None:
        return _unavailable("path_not_provided")
    try:
        payload = _read_json_object(path)
    except FileNotFoundError:
        return _unavailable("file_missing")
    except NotADirectoryError:
        return _unavailable("path_invalid")
    except IsADirectoryError:
        return _unavailable("path_is_directory")
    except OSError:
        return _unavailable("file_unreadable")
    except (UnicodeDecodeError, ValueError):
        return _unavailable("json_invalid")
    if not isinstance(payload, dict):
        return _unavailable("payload_not_object")
    schema_version = payload.get("schema_version")
    stored = payload.get("output_digest")
    if not isinstance(schema_version, str) or not schema_version or not isinstance(stored, str) or not stored:
        result = _unavailable("required_field_missing")
        if isinstance(schema_version, str):
            result["schema_version"] = schema_version
        if isinstance(stored, str):
            result["output_digest"] = stored
        return result
    unsigned = {key: value for key, value in payload.items() if key != "output_digest"}
    recomputed = "sha256:" + hashlib.sha256(_canonical_bytes(unsigned)).hexdigest()
    verified = hmac.compare_digest(recomputed, stored)
    return {
        "schema_version": schema_version,
        "available": True,
        "digest_verified": verified,
        "output_digest": stored,
        "reason": "" if verified else "output_digest_mismatch",
    }


def load_memory_quality_digests(path) -> List[Mapping[str, Any]]:
    """Surface report_digest presence entries from MEMORY_QUALITY_EVIDENCE.json.

    One entry per adversarial_corpus_* sub-report (sorted by key), followed by
    a top-level entry carrying the document schema. Digests are surfaced as
    present-or-absent only; verification of corpus digests needs the corpus
    fixtures and is out of scope here. Missing or corrupt files yield an
    empty list; this function never raises.
    """
    if path is None:
        return []
    try:
        payload = _read_json_object(path)
    except (OSError, UnicodeDecodeError, ValueError):
        return []
    if not isinstance(payload, dict):
        return []
    entries: List[Mapping[str, Any]] = []
    sub_keys = sorted(key for key in payload if key.startswith("adversarial_corpus_") and isinstance(payload[key], dict))
    for key in sub_keys:
        report = payload[key]
        digest = report.get("report_digest")
        digest_present = isinstance(digest, str) and bool(digest)
        entries.append({
            "corpus_schema_version": str(report.get("schema_version", "")),
            "report_digest": str(digest) if digest_present else "",
            "digest_present": digest_present,
        })
    top_schema = payload.get("schema_version")
    entries.append({
        "corpus_schema_version": str(top_schema) if isinstance(top_schema, str) else "",
        "report_digest": "",
        "digest_present": False,
    })
    return entries


def project_evidence(workload_path=None, memory_quality_path=None) -> Mapping[str, Any]:
    """Build the deterministic evidence projection consumed by HealthServer.

    Both paths are optional; safe defaults are emitted when a path is absent.
    The output contains no timestamps and depends only on file contents.
    """
    workload = load_workload_evidence(workload_path)
    digests = load_memory_quality_digests(memory_quality_path)
    return {
        "schema_version": EVIDENCE_PROJECTION_SCHEMA,
        "claim_boundary": "committed_local_evidence_read_only_fail_closed",
        "workload_evidence": dict(workload),
        "memory_quality_digests": [dict(entry) for entry in digests],
    }


__all__ = ["EVIDENCE_PROJECTION_SCHEMA", "load_workload_evidence", "load_memory_quality_digests", "project_evidence"]

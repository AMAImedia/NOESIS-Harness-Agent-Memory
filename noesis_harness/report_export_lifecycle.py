"""Verify signed report-export lifecycle evidence without upgrading claims.

Patterns adapted from signed report export receipts, append-only ingestion
ledgers, session-stream ordering, and claim-conservative evidence aggregation.
Lifecycle events are audit evidence only, never execution or comparative proof.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .report_export_action import LIFECYCLE_SCHEMA


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(dict(value), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def _verify_signature(event: Mapping[str, Any], key: bytes) -> bool:
    unsigned = dict(event)
    signature = str(unsigned.pop("signature", ""))
    return bool(signature) and hmac.compare_digest(signature, hmac.new(key, _canonical(unsigned), hashlib.sha256).hexdigest())


def verify_lifecycle_events(events: Sequence[Mapping[str, Any]], signing_key: bytes) -> Mapping[str, Any]:
    if not isinstance(signing_key, bytes) or len(signing_key) < 16:
        raise ValueError("signing_key_too_short")
    if not isinstance(events, Sequence) or isinstance(events, (str, bytes)) or not events:
        return {"schema_version": LIFECYCLE_SCHEMA, "status": "not_run", "reason": "lifecycle_events_required", "event_count": 0, "claim": False}
    seen: set[str] = set()
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    normalized: list[dict[str, Any]] = []
    for event in events:
        if not isinstance(event, Mapping) or event.get("schema_version") != LIFECYCLE_SCHEMA:
            return {"schema_version": LIFECYCLE_SCHEMA, "status": "blocked", "reason": "lifecycle_schema_invalid", "event_count": len(normalized), "claim": False}
        event_id = str(event.get("event_id", ""))
        action_id = str(event.get("action_id", ""))
        session_id = str(event.get("session_id", ""))
        status = str(event.get("status", ""))
        if not event_id or not action_id or not session_id or status not in {"approved", "exporting", "completed", "blocked"}:
            return {"schema_version": LIFECYCLE_SCHEMA, "status": "blocked", "reason": "lifecycle_identity_incomplete", "event_count": len(normalized), "claim": False}
        if event_id in seen:
            return {"schema_version": LIFECYCLE_SCHEMA, "status": "blocked", "reason": "duplicate_lifecycle_event_id", "event_count": len(normalized), "claim": False}
        if not _verify_signature(event, signing_key):
            return {"schema_version": LIFECYCLE_SCHEMA, "status": "blocked", "reason": "lifecycle_signature_invalid", "event_count": len(normalized), "claim": False}
        seen.add(event_id)
        key = (session_id, action_id)
        grouped.setdefault(key, []).append(event)
        normalized.append({"event_id": event_id, "session_id": session_id, "action_id": action_id, "status": status, "reason": str(event.get("reason", ""))[:160]})
    for group in grouped.values():
        statuses = [str(item["status"]) for item in group]
        if statuses[:3] not in (["approved", "exporting", "completed"], ["approved", "completed"], ["approved", "exporting", "blocked"], ["approved", "blocked"]):
            if not (statuses and statuses[0] == "blocked"):
                return {"schema_version": LIFECYCLE_SCHEMA, "status": "blocked", "reason": "lifecycle_order_invalid", "event_count": len(normalized), "claim": False}
        if "completed" in statuses and statuses.count("completed") > 1:
            return {"schema_version": LIFECYCLE_SCHEMA, "status": "blocked", "reason": "duplicate_completed_event", "event_count": len(normalized), "claim": False}
    return {"schema_version": LIFECYCLE_SCHEMA, "status": "passed", "reason": "signed_lifecycle_audit_verified", "event_count": len(normalized), "events": normalized, "audit_digest": _digest(normalized), "claim": False, "execution_claim": False, "comparative_claim": False}


def verify_lifecycle_file(path: str | Path, signing_key: bytes) -> Mapping[str, Any]:
    events: list[Mapping[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            return {"schema_version": LIFECYCLE_SCHEMA, "status": "blocked", "reason": "lifecycle_json_invalid", "event_count": len(events), "claim": False}
        events.append(value)
    return verify_lifecycle_events(events, signing_key)


def lifecycle_audit_only_projection(verification: Mapping[str, Any]) -> Mapping[str, Any]:
    return {"status": str(verification.get("status", "blocked")), "reason": str(verification.get("reason", "")), "event_count": int(verification.get("event_count", 0)), "audit_digest": str(verification.get("audit_digest", "")), "claim": False, "execution_claim": False, "comparative_claim": False, "claim_boundary": "audit_only_lifecycle_evidence"}


__all__ = ["verify_lifecycle_events", "verify_lifecycle_file", "lifecycle_audit_only_projection"]

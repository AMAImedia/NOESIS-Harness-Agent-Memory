"""Operator-owned signed report export action.

Patterns adapted from delegated resume actions, signed report bundles, operator
session authorization, and append-only audit receipts. The handler exports a
bounded snapshot only; it never executes providers or external lanes.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from .report_bundle import build_report_bundle

SCHEMA_VERSION = "noesis.report-export-action.v1"
RECEIPT_SCHEMA = "noesis.report-export-receipt.v1"
REQUIRED_SCOPE = "report:export"


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(dict(value), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


class ReportExportActionError(ValueError):
    """Raised when a report export action fails closed."""


@dataclass(frozen=True)
class ReportExportAction:
    action_id: str
    operator_id: str
    session_id: str
    output_name: str
    snapshot_digest: str
    signature: str
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def sign(cls, *, action_id: str, operator_id: str, session_id: str, output_name: str, snapshot_digest: str, signing_key: bytes) -> "ReportExportAction":
        unsigned = {"schema_version": SCHEMA_VERSION, "action_id": action_id, "operator_id": operator_id, "session_id": session_id, "output_name": output_name, "snapshot_digest": snapshot_digest}
        if not action_id or not operator_id or not session_id or not output_name or len(snapshot_digest) != 64:
            raise ValueError("report_export_action_identity_required")
        return cls(action_id, operator_id, session_id, output_name, snapshot_digest, hmac.new(signing_key, _canonical(unsigned), hashlib.sha256).hexdigest())

    def unsigned(self) -> dict[str, Any]:
        return {"schema_version": self.schema_version, "action_id": self.action_id, "operator_id": self.operator_id, "session_id": self.session_id, "output_name": self.output_name, "snapshot_digest": self.snapshot_digest}

    def to_mapping(self) -> dict[str, Any]:
        return {**self.unsigned(), "signature": self.signature}

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ReportExportAction":
        return cls(str(value.get("action_id", "")), str(value.get("operator_id", "")), str(value.get("session_id", "")), str(value.get("output_name", "")), str(value.get("snapshot_digest", "")), str(value.get("signature", "")), str(value.get("schema_version", "")))


class ReportExportActionExecutor:
    def __init__(self, output_dir: str | os.PathLike[str], audit_path: str | os.PathLike[str], *, signing_key: bytes, snapshot_provider: Callable[[], Mapping[str, Any]], required_scope: str = REQUIRED_SCOPE):
        if not isinstance(signing_key, bytes) or len(signing_key) < 16:
            raise ValueError("signing_key_too_short")
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.audit_path = Path(audit_path)
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        self.signing_key = signing_key
        self.snapshot_provider = snapshot_provider
        self.required_scope = required_scope
        self._used: set[str] = set()
        if self.audit_path.exists():
            for line in self.audit_path.read_text(encoding="utf-8").splitlines():
                try:
                    value = json.loads(line)
                    if value.get("action_id"):
                        self._used.add(str(value["action_id"]))
                except json.JSONDecodeError:
                    continue

    def _authorize(self, action: ReportExportAction, context: Any) -> None:
        if action.schema_version != SCHEMA_VERSION or not action.action_id or not action.operator_id or not action.session_id or len(action.snapshot_digest) != 64:
            raise ReportExportActionError("action_schema_invalid")
        if not getattr(context, "authenticated", False) or str(getattr(context, "operator_id", "")) != action.operator_id:
            raise ReportExportActionError("operator_identity_mismatch")
        if self.required_scope not in tuple(getattr(context, "scopes", ())):
            raise ReportExportActionError("scope_required")
        if not hmac.compare_digest(action.signature, hmac.new(self.signing_key, _canonical(action.unsigned()), hashlib.sha256).hexdigest()):
            raise ReportExportActionError("signature_invalid")
        if action.action_id in self._used:
            raise ReportExportActionError("action_replayed")
        if Path(action.output_name).name != action.output_name or action.output_name in {"", ".", ".."} or not action.output_name.endswith(".zip"):
            raise ReportExportActionError("output_name_invalid")

    def handle(self, action: ReportExportAction, context: Any) -> Mapping[str, Any]:
        self._authorize(action, context)
        snapshot = self.snapshot_provider()
        if not isinstance(snapshot, Mapping):
            raise ReportExportActionError("snapshot_provider_must_return_object")
        if _digest(snapshot) != action.snapshot_digest:
            raise ReportExportActionError("snapshot_digest_drift")
        output = (self.output_dir / action.output_name).resolve()
        if self.output_dir not in output.parents:
            raise ReportExportActionError("output_path_escape")
        from scripts.export_operator_report import export_snapshot
        result = export_snapshot(snapshot, str(output), self.signing_key)
        receipt_unsigned = {"schema_version": RECEIPT_SCHEMA, "action_id": action.action_id, "operator_id": action.operator_id, "session_id": action.session_id, "output_name": action.output_name, "snapshot_digest": action.snapshot_digest, "bundle_digest": str(result["bundle_digest"]), "status": "completed", "created_at": int(time.time())}
        receipt = {**receipt_unsigned, "signature": hmac.new(self.signing_key, _canonical(receipt_unsigned), hashlib.sha256).hexdigest()}
        with self.audit_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(receipt, sort_keys=True, ensure_ascii=False) + "\n")
        self._used.add(action.action_id)
        return {"status": "completed", "output_name": action.output_name, "bundle_digest": result["bundle_digest"], "audit_receipt": {"schema_version": RECEIPT_SCHEMA, "action_id": action.action_id, "status": "completed", "signature": receipt["signature"]}}


__all__ = ["SCHEMA_VERSION", "RECEIPT_SCHEMA", "REQUIRED_SCOPE", "ReportExportAction", "ReportExportActionError", "ReportExportActionExecutor"]

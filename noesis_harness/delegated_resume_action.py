"""Authenticated operator action for delegated resume.

Patterns adapted from the project's signed mutation receipts, operator session
actions, and durable single-use approval records. This module never discovers
credentials and never makes telemetry writable.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional

from .event_store import EventStore

SCHEMA_VERSION = "noesis.delegated-resume-action.v1"
REQUIRED_SCOPE = "task:resume"


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(dict(value), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class DelegatedResumeAction:
    action_id: str
    operator_id: str
    session_id: str
    task_id: str
    approval_id: str
    request_digest: str
    signature: str
    schema_version: str = SCHEMA_VERSION

    def unsigned(self) -> dict[str, str]:
        return {"schema_version": self.schema_version, "action_id": self.action_id, "operator_id": self.operator_id, "session_id": self.session_id, "task_id": self.task_id, "approval_id": self.approval_id, "request_digest": self.request_digest}

    def to_mapping(self) -> dict[str, str]:
        return {**self.unsigned(), "signature": self.signature}

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "DelegatedResumeAction":
        if not isinstance(value, Mapping) or value.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("unsupported_delegated_resume_action_schema")
        return cls(*(str(value.get(key, "")) for key in ("action_id", "operator_id", "session_id", "task_id", "approval_id", "request_digest", "signature")))

    @classmethod
    def sign(cls, *, action_id: str, operator_id: str, session_id: str, task_id: str, approval_id: str, request_digest: str, signing_key: bytes) -> "DelegatedResumeAction":
        if not isinstance(signing_key, bytes) or len(signing_key) < 16:
            raise ValueError("signing_key_too_short")
        provisional = cls(action_id, operator_id, session_id, task_id, approval_id, request_digest, "")
        signature = hmac.new(signing_key, _canonical(provisional.unsigned()), hashlib.sha256).hexdigest()
        return cls(action_id, operator_id, session_id, task_id, approval_id, request_digest, signature)


@dataclass(frozen=True)
class DelegatedResumeActionReceipt:
    action_id: str
    operator_id: str
    session_id: str
    task_id: str
    status: str
    payload_digest: str
    signature: str
    schema_version: str = "noesis.delegated-resume-receipt.v1"

    def unsigned(self) -> dict[str, str]:
        return {"schema_version": self.schema_version, "action_id": self.action_id, "operator_id": self.operator_id, "session_id": self.session_id, "task_id": self.task_id, "status": self.status, "payload_digest": self.payload_digest}

    def to_mapping(self) -> dict[str, str]:
        return {**self.unsigned(), "signature": self.signature}


class DelegatedResumeActionError(ValueError):
    """Raised when an operator resume action fails closed."""


class DelegatedResumeActionExecutor:
    """Validate, execute once, and durably sign an operator resume action."""

    def __init__(self, event_path: str, *, signing_key: bytes, resume_callback: Callable[[DelegatedResumeAction], Mapping[str, Any]], required_scope: str = REQUIRED_SCOPE):
        if not isinstance(signing_key, bytes) or len(signing_key) < 16:
            raise ValueError("signing_key_too_short")
        if not callable(resume_callback):
            raise ValueError("resume_callback_required")
        self.events = EventStore(event_path)
        self.signing_key = signing_key
        self.resume_callback = resume_callback
        self.required_scope = str(required_scope)

    def _existing(self, action_id: str) -> Optional[Mapping[str, Any]]:
        for event in self.events.iter_events():
            payload = event.get("payload") or {}
            if event.get("type") == "delegated_resume_action_completed" and payload.get("action_id") == action_id:
                return dict(payload)
        return None

    def _verify(self, action: DelegatedResumeAction) -> None:
        expected = hmac.new(self.signing_key, _canonical(action.unsigned()), hashlib.sha256).hexdigest()
        if action.schema_version != SCHEMA_VERSION or not hmac.compare_digest(expected, action.signature):
            raise DelegatedResumeActionError("delegated_resume_action_signature_invalid")
        if not all((action.action_id, action.operator_id, action.session_id, action.task_id, action.approval_id, action.request_digest)):
            raise DelegatedResumeActionError("delegated_resume_action_identity_required")

    def handle(self, action: DelegatedResumeAction, context: Any) -> Mapping[str, Any]:
        if not isinstance(action, DelegatedResumeAction):
            raise DelegatedResumeActionError("delegated_resume_action_required")
        self._verify(action)
        if context is None or not bool(getattr(context, "authenticated", False)) or str(getattr(context, "operator_id", "")) != action.operator_id:
            raise DelegatedResumeActionError("operator_identity_mismatch")
        scopes = tuple(str(item) for item in getattr(context, "scopes", ()))
        if self.required_scope not in scopes:
            raise DelegatedResumeActionError("delegated_resume_scope_required")
        existing = self._existing(action.action_id)
        if existing is not None:
            return {"status": "replayed", "receipt": existing}
        payload = action.to_mapping()
        try:
            result = self.resume_callback(action)
            status = "completed"
        except Exception as exc:
            result = {"reason": type(exc).__name__}
            status = "rejected"
        receipt_payload = {"action": payload, "result": result, "status": status}
        unsigned = {"schema_version": "noesis.delegated-resume-receipt.v1", "action_id": action.action_id, "operator_id": action.operator_id, "session_id": action.session_id, "task_id": action.task_id, "status": status, "payload_digest": _digest(receipt_payload)}
        signature = hmac.new(self.signing_key, _canonical(unsigned), hashlib.sha256).hexdigest()
        receipt = DelegatedResumeActionReceipt(action.action_id, action.operator_id, action.session_id, action.task_id, status, unsigned["payload_digest"], signature)
        record = {"action_id": action.action_id, "operator_id": action.operator_id, "session_id": action.session_id, "task_id": action.task_id, "status": status, "result": dict(result) if isinstance(result, Mapping) else {"result": str(result)[:256]}, "audit_receipt": receipt.to_mapping(), "created_at": time.time()}
        self.events.append("delegated_resume_action_completed", record, event_id="delegated-resume-action:" + action.action_id)
        return record


__all__ = ["SCHEMA_VERSION", "REQUIRED_SCOPE", "DelegatedResumeAction", "DelegatedResumeActionReceipt", "DelegatedResumeActionError", "DelegatedResumeActionExecutor"]

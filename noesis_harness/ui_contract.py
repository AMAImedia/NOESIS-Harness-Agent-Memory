"""Versioned stdlib-only contract for the optional NOESIS control plane."""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence, Tuple

CONTRACT_VERSION = "1.0"
_SECRET_KEY = re.compile(r"(?i)(?:token|secret|password|credential|authorization|api[_-]?key|private[_-]?key)")
_ALLOWED_STATUSES = frozenset({"ready", "degraded", "unavailable", "denied", "invalid_request", "upstream_error"})


class UIContractError(ValueError):
    """Raised only for invalid local contract inputs."""


def new_request_id() -> str:
    return uuid.uuid4().hex


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): "[REDACTED]" if _SECRET_KEY.search(str(key)) else _redact(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact(item) for item in value]
    return value


def _status(status: str) -> str:
    if status not in _ALLOWED_STATUSES:
        raise UIContractError(f"unsupported status: {status}")
    return status


@dataclass(frozen=True)
class UIEnvelope:
    ok: bool
    status: str
    data: Any = None
    error: Any = None
    request_id: str = field(default_factory=new_request_id)
    capabilities: Mapping[str, str] = field(default_factory=dict)
    unavailable_reasons: Tuple[str, ...] = ()
    contract_version: str = CONTRACT_VERSION

    def __post_init__(self) -> None:
        _status(self.status)
        if not self.request_id or not isinstance(self.request_id, str):
            raise UIContractError("request_id must be a non-empty string")
        if self.ok and self.error is not None:
            raise UIContractError("successful envelope cannot contain error")
        if not self.ok and self.error is None:
            raise UIContractError("failed envelope requires error")
        if self.contract_version != CONTRACT_VERSION:
            raise UIContractError("unsupported contract version")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["data"] = _redact(payload["data"])
        payload["error"] = _redact(payload["error"])
        payload["capabilities"] = _redact(payload["capabilities"])
        payload["unavailable_reasons"] = list(self.unavailable_reasons)
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def success(data: Any = None, *, status: str = "ready", capabilities: Mapping[str, str] = (), unavailable_reasons: Sequence[str] = (), request_id: str | None = None) -> UIEnvelope:
    return UIEnvelope(True, _status(status), data, None, request_id or new_request_id(), dict(capabilities), tuple(str(item) for item in unavailable_reasons))


def failure(status: str, code: str, message: str, *, request_id: str | None = None, unavailable_reasons: Sequence[str] = ()) -> UIEnvelope:
    if status not in {"denied", "invalid_request", "upstream_error", "unavailable"}:
        raise UIContractError("failure status must describe a failed request")
    return UIEnvelope(False, status, None, {"code": str(code), "message": str(message)}, request_id or new_request_id(), {}, tuple(str(item) for item in unavailable_reasons))


def health_payload(*, runtime_version: str, readiness: str, binding: str, capabilities: Mapping[str, str], unavailable_reasons: Sequence[str] = ()) -> UIEnvelope:
    if readiness not in {"ready", "degraded", "unavailable"}:
        raise UIContractError("invalid readiness status")
    capability_map = {str(key): _status(str(value)) for key, value in capabilities.items()}
    reasons = tuple(str(item) for item in unavailable_reasons)
    status = "degraded" if readiness == "ready" and reasons else readiness
    return success({"runtime_version": str(runtime_version), "readiness": readiness, "binding": str(binding)}, status=status, capabilities=capability_map, unavailable_reasons=reasons)


def model_payload(records: Sequence[Mapping[str, Any]], *, provider_registry_status: str = "ready", unavailable_reasons: Sequence[str] = ()) -> UIEnvelope:
    models = []
    for raw in records:
        if not isinstance(raw, Mapping) or not raw.get("id") or not raw.get("provider"):
            raise UIContractError("model record requires id and provider")
        capabilities = raw.get("capabilities", {})
        if not isinstance(capabilities, Mapping):
            raise UIContractError("model capabilities must be a mapping")
        models.append({
            "id": str(raw["id"]),
            "provider": str(raw["provider"]),
            "endpoint_kind": str(raw.get("endpoint_kind", "unknown")),
            "status": str(raw.get("status", "ready")),
            "capabilities": {str(key): bool(value) for key, value in capabilities.items()},
        })
    status = _status(provider_registry_status)
    return success({"models": models}, status=status, capabilities={"provider_registry": status}, unavailable_reasons=unavailable_reasons)


__all__ = ["CONTRACT_VERSION", "UIContractError", "UIEnvelope", "failure", "health_payload", "model_payload", "new_request_id", "success"]

"""Provider gateway and isolation telemetry contracts.

The gateway is deliberately transport-agnostic: real network calls require an
injected transport and explicit ``network_enabled=True``. Credentials are
resolved outside this module and are never serialized into child payloads.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

from .resource_lineage import ObservationLedger

GATEWAY_SCHEMA = "noesis.gateway.v1"


class GatewayPolicyError(ValueError):
    """Raised when a gateway request cannot pass policy."""


@dataclass(frozen=True)
class ProviderRoute:
    provider_id: str
    base_url: str
    capabilities: Tuple[str, ...] = ()
    model_ids: Tuple[str, ...] = ()
    status: str = "unknown"
    network_class: str = "external"


@dataclass(frozen=True)
class GatewayRequest:
    session_id: str
    agent_id: str
    provider_id: str
    model: str
    capability: str
    payload: Mapping[str, Any]
    target: str = "external:provider"
    explicit_approval: bool = False


@dataclass(frozen=True)
class GatewayResponse:
    ok: bool
    status: str
    provider_id: str
    request_id: str
    data: Mapping[str, Any] = field(default_factory=dict)
    reason: str = ""


class GatewayRouter:
    def __init__(self, *, ledger: Optional[ObservationLedger] = None, max_payload_bytes: int = 64 * 1024):
        self.ledger = ledger
        self.max_payload_bytes = max_payload_bytes
        self._routes: Dict[str, ProviderRoute] = {}
        self._health: Dict[str, Dict[str, Any]] = {}

    def register(self, route: ProviderRoute) -> None:
        if not route.provider_id or not route.base_url or route.network_class not in {"loopback", "lan", "external"}:
            raise GatewayPolicyError("invalid_provider_route")
        self._routes[route.provider_id] = route
        self._health.setdefault(route.provider_id, {"status": route.status, "checks": 0, "last_checked": None})

    def health_snapshot(self) -> Mapping[str, Any]:
        return {"schema_version": GATEWAY_SCHEMA, "providers": [{"provider_id": route.provider_id, "base_url": route.base_url, "capabilities": list(route.capabilities), "model_ids": list(route.model_ids), "network_class": route.network_class, "health": dict(self._health.get(route.provider_id, {}))} for route in self._routes.values()]}

    def record_health(self, provider_id: str, status: str, *, latency_ms: Optional[float] = None, reason: str = "") -> None:
        if provider_id not in self._routes or status not in {"ready", "degraded", "unavailable"}:
            raise GatewayPolicyError("unknown_provider_health")
        self._health[provider_id] = {"status": status, "checks": int(self._health.get(provider_id, {}).get("checks", 0)) + 1, "latency_ms": latency_ms, "reason": reason, "last_checked": time.time()}

    def route(self, request: GatewayRequest, transport: Optional[Callable[[ProviderRoute, Mapping[str, Any]], Mapping[str, Any]]] = None) -> GatewayResponse:
        route = self._routes.get(request.provider_id)
        request_id = "gw:" + hashlib.sha256(json.dumps({"session_id": request.session_id, "agent_id": request.agent_id, "provider_id": request.provider_id, "model": request.model, "capability": request.capability, "payload": request.payload}, sort_keys=True, default=str).encode()).hexdigest()
        if route is None:
            return GatewayResponse(False, "denied", request.provider_id, request_id, reason="unknown_provider")
        if request.capability not in route.capabilities:
            return GatewayResponse(False, "denied", request.provider_id, request_id, reason="capability_not_supported")
        if route.model_ids and request.model not in route.model_ids:
            return GatewayResponse(False, "denied", request.provider_id, request_id, reason="model_not_pinned")
        body = json.dumps(dict(request.payload), ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        if len(body) > self.max_payload_bytes:
            return GatewayResponse(False, "denied", request.provider_id, request_id, reason="payload_budget_exceeded")
        if route.network_class == "external" and not request.explicit_approval:
            return GatewayResponse(False, "denied", request.provider_id, request_id, reason="external_network_requires_approval")
        if route.network_class == "external" and self.ledger is not None:
            decision = self.ledger.decide_egress(request.session_id, request.agent_id, request.target, explicit_approval=request.explicit_approval)
            if not decision.allowed:
                return GatewayResponse(False, "denied", request.provider_id, request_id, reason=decision.reason)
        if transport is None:
            return GatewayResponse(False, "not_run", request.provider_id, request_id, reason="transport_not_injected")
        try:
            result = dict(transport(route, {"model": request.model, "capability": request.capability, "payload": dict(request.payload)}))
        except Exception:
            self.record_health(request.provider_id, "degraded", reason="transport_error")
            return GatewayResponse(False, "error", request.provider_id, request_id, reason="transport_error")
        self.record_health(request.provider_id, "ready")
        return GatewayResponse(True, "ok", request.provider_id, request_id, data=result)


__all__ = ["GATEWAY_SCHEMA", "GatewayPolicyError", "GatewayRequest", "GatewayResponse", "GatewayRouter", "ProviderRoute"]

"""Capability-based approval gate for tools, providers and executable skills.

Gatekeeper prepares and audits actions. It never performs the side effect itself;
an executor must consume an explicitly committed, approved action later.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from .event_store import EventStore

GATE_SCHEMA = "noesis.gatekeeper.v1"
CAPABILITIES = frozenset({
    "memory.read", "models.read", "workspace.read", "workspace.write",
    "tool.invoke", "skill.execute", "network.read", "network.write",
})
SIDE_EFFECTS = frozenset({"none", "read", "write", "external"})
_APPROVAL_REQUIRED = frozenset({"workspace.write", "tool.invoke", "skill.execute", "network.read", "network.write"})
_TERMINAL = frozenset({"rejected", "committed", "expired"})


class GatekeeperError(ValueError):
    """Raised when a capability request violates policy."""


@dataclass(frozen=True)
class CapabilityRequest:
    session_id: str
    task_id: str
    agent_id: str
    capability: str
    action: str
    target: str
    side_effect: str
    arguments: Mapping[str, Any]
    request_id: str = ""

    def normalized_id(self) -> str:
        if self.request_id:
            return self.request_id
        seed = "\x00".join((self.session_id, self.task_id, self.agent_id, self.capability, self.action, self.target))
        return "req_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]


@dataclass(frozen=True)
class GateDecision:
    request_id: str
    status: str
    reason: str
    simulated: Mapping[str, Any]


class Gatekeeper:
    """Durable prepare/approve/reject/commit gate with no embedded executor."""

    def __init__(self, event_path: str):
        self.events = EventStore(event_path)

    @staticmethod
    def _safe(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {str(key): Gatekeeper._safe(item) for key, item in value.items() if str(key).lower() not in {"token", "api_key", "apikey", "authorization", "password", "secret"}}
        if isinstance(value, (list, tuple)):
            return [Gatekeeper._safe(item) for item in value]
        if isinstance(value, str):
            return value.replace("ghp_", "[REDACTED]ghp_").replace("hf_", "[REDACTED]hf_")[:8192]
        if value is None or isinstance(value, (bool, int, float)):
            return value
        return repr(value)[:8192]

    def _state(self) -> dict[str, dict[str, Any]]:
        state: dict[str, dict[str, Any]] = {}
        for event in self.events.iter_events() or ():
            payload = event.get("payload") or {}
            if event.get("type") == "gate_prepared":
                state[payload["request_id"]] = dict(payload)
            elif event.get("type") == "gate_transition":
                record = state.get(payload["request_id"])
                if record:
                    record["status"] = payload["status"]
                    record["reason"] = payload["reason"]
                    record["updated_at"] = payload["updated_at"]
        return state

    def _append(self, event_type: str, payload: Mapping[str, Any], command_id: str) -> str:
        safe = self._safe(dict(payload))
        safe["schema_version"] = GATE_SCHEMA
        safe["command_id"] = command_id
        return self.events.append(event_type, safe, event_id="gate_" + command_id)

    def prepare(self, request: CapabilityRequest) -> GateDecision:
        if not request.session_id or not request.task_id or not request.agent_id:
            raise GatekeeperError("session, task and agent identity are required")
        if request.capability not in CAPABILITIES:
            raise GatekeeperError("capability_not_registered:%s" % request.capability)
        if request.side_effect not in SIDE_EFFECTS:
            raise GatekeeperError("invalid_side_effect")
        if request.capability == "network.write" and request.side_effect != "external":
            raise GatekeeperError("network.write_requires_external_side_effect")
        rid = request.normalized_id()
        existing = self._state().get(rid)
        if existing:
            return GateDecision(rid, existing["status"], existing.get("reason", "idempotent_replay"), existing.get("simulated", {}))
        status = "waiting_approval" if request.capability in _APPROVAL_REQUIRED or request.side_effect in {"write", "external"} else "prepared"
        reason = "human_approval_required" if status == "waiting_approval" else "read_only_capability"
        simulated = {"simulated": True, "action": request.action, "target": request.target, "side_effect": request.side_effect, "note": "No external side effect was performed."}
        now = time.time()
        self._append("gate_prepared", {"request_id": rid, "session_id": request.session_id, "task_id": request.task_id, "agent_id": request.agent_id, "capability": request.capability, "action": request.action, "target": request.target, "side_effect": request.side_effect, "arguments": request.arguments, "status": status, "reason": reason, "simulated": simulated, "created_at": now, "updated_at": now}, rid + ":prepare")
        return GateDecision(rid, status, reason, simulated)

    def _transition(self, request_id: str, status: str, reason: str, command_id: Optional[str] = None) -> GateDecision:
        record = self._state().get(request_id)
        if not record:
            raise GatekeeperError("unknown_request")
        current = record["status"]
        allowed = {"waiting_approval": {"approved", "rejected"}, "prepared": {"committed", "rejected"}, "approved": {"committed", "rejected"}}
        if status not in allowed.get(current, set()):
            raise GatekeeperError("invalid_gate_transition:%s->%s" % (current, status))
        command = command_id or uuid.uuid4().hex
        self._append("gate_transition", {"request_id": request_id, "status": status, "reason": reason, "updated_at": time.time()}, request_id + ":" + command)
        return GateDecision(request_id, status, reason, record.get("simulated", {}))

    def approve(self, request_id: str) -> GateDecision:
        return self._transition(request_id, "approved", "human_approved")

    def reject(self, request_id: str, reason: str = "human_rejected") -> GateDecision:
        return self._transition(request_id, "rejected", reason)

    def commit(self, request_id: str) -> GateDecision:
        """Commit permission only; an external executor must still perform the action."""
        return self._transition(request_id, "committed", "permission_committed_not_executed")

    def get(self, request_id: str) -> Optional[Mapping[str, Any]]:
        return self._state().get(request_id)


__all__ = ["GATE_SCHEMA", "CAPABILITIES", "CapabilityRequest", "GateDecision", "Gatekeeper", "GatekeeperError"]

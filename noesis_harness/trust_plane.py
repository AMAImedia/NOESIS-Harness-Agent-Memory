"""End-to-end Trust Plane policy boundary for child skills."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence, Tuple

from .child_execution import ChildExecutionRuntime, ExecutionRequest, ExecutionResult
from .context_firewall import ContextFirewall, ContextItem, ContextDecision
from .gatekeeper import CapabilityRequest, GateDecision, Gatekeeper
from .resource_lineage import Observation, ObservationLedger, EgressDecision
from .event_store import EventStore


@dataclass(frozen=True)
class TrustPlaneDecision:
    allowed: bool
    reason: str
    context: ContextDecision
    egress: EgressDecision | None = None
    gate: GateDecision | None = None
    execution: ExecutionResult | None = None


class TrustPlane:
    """Compose context, lineage, approval and child execution as one fail-closed boundary."""

    def __init__(self, gatekeeper: Gatekeeper, lineage: ObservationLedger, *, firewall: ContextFirewall | None = None, child_runtime: ChildExecutionRuntime | None = None, audit_path: str | None = None):
        self.gatekeeper = gatekeeper
        self.lineage = lineage
        self.firewall = firewall or ContextFirewall()
        self.child_runtime = child_runtime or ChildExecutionRuntime(gatekeeper)
        self.audit = EventStore(audit_path) if audit_path else None

    @staticmethod
    def _canonical(value: Mapping[str, Any]) -> bytes:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")

    def _audit_decision(self, decision: TrustPlaneDecision) -> None:
        if self.audit is None:
            return
        previous = "0" * 64
        for event in self.audit.iter_events() or ():
            previous = str((event.get("payload") or {}).get("event_hash", previous))
        payload = {
            "schema_version": "noesis.trust-plane-decision.v1",
            "allowed": decision.allowed,
            "reason": decision.reason,
            "context_digest": decision.context.digest,
            "included_ids": list(decision.context.included_ids),
            "redacted_ids": list(decision.context.redacted_ids),
            "truncated_ids": list(decision.context.truncated_ids),
            "included_resource_ids": list(decision.context.included_resource_ids),
            "egress": {"allowed": decision.egress.allowed, "reason": decision.egress.reason, "resources": list(decision.egress.observed_resources), "blocked": list(decision.egress.blocked_sensitivities)} if decision.egress else None,
            "gate": {"request_id": decision.gate.request_id, "status": decision.gate.status, "reason": decision.gate.reason} if decision.gate else None,
            "execution": {"status": decision.execution.status, "reason": decision.execution.reason} if decision.execution else None,
        }
        payload["prev_hash"] = previous
        payload["event_hash"] = hashlib.sha256(self._canonical(payload)).hexdigest()
        self.audit.append("trust_plane_decision", payload, event_id="trust_" + payload["event_hash"][:32])

    def verify_audit_chain(self) -> bool:
        if self.audit is None:
            return True
        previous = "0" * 64
        for event in self.audit.iter_events() or ():
            payload = dict(event.get("payload") or {})
            expected = payload.pop("event_hash", None)
            if payload.get("prev_hash") != previous or expected != hashlib.sha256(self._canonical(payload)).hexdigest():
                return False
            previous = str(expected)
        return True

    def run_skill(self, *, session_id: str, task_id: str, agent_id: str, context_items: Sequence[ContextItem], request: CapabilityRequest, execution: ExecutionRequest, explicit_approval: bool = False) -> TrustPlaneDecision:
        context = self.firewall.build(tuple(context_items), explicit_approval=explicit_approval, allowed_sensitivities=("public", "internal", "sensitive", "restricted") if explicit_approval else ("public", "internal"))
        for item in context_items:
            if item.resource_id:
                self.lineage.record(Observation(session_id, agent_id, item.resource_id, "context", item.sensitivity))
        egress = self.lineage.decide_egress(session_id, agent_id, "child:" + execution.request_id, explicit_approval=explicit_approval)
        if not egress.allowed:
            decision = TrustPlaneDecision(False, "lineage_egress_denied:" + egress.reason, context, egress=egress)
            self._audit_decision(decision)
            return decision
        try:
            gate = self.gatekeeper.prepare(request)
        except Exception as exc:
            decision = TrustPlaneDecision(False, "gatekeeper_denied:" + str(exc), context, egress=egress)
            self._audit_decision(decision)
            return decision
        if gate.status == "waiting_approval":
            if not explicit_approval:
                decision = TrustPlaneDecision(False, "approval_required", context, egress=egress, gate=gate)
                self._audit_decision(decision)
                return decision
            gate = self.gatekeeper.approve(gate.request_id)
        if gate.status != "committed":
            gate = self.gatekeeper.commit(gate.request_id)
        result = self.child_runtime.run(execution)
        decision = TrustPlaneDecision(result.status in {"completed"}, "child_execution:" + result.reason, context, egress=egress, gate=gate, execution=result)
        self._audit_decision(decision)
        return decision


__all__ = ["TrustPlane", "TrustPlaneDecision"]

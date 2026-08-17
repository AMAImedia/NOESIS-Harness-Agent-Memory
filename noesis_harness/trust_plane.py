"""End-to-end Trust Plane policy boundary for child skills."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

from .child_execution import ChildExecutionRuntime, ExecutionRequest, ExecutionResult
from .context_firewall import ContextFirewall, ContextItem, ContextDecision
from .gatekeeper import CapabilityRequest, GateDecision, Gatekeeper
from .resource_lineage import Observation, ObservationLedger, EgressDecision


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

    def __init__(self, gatekeeper: Gatekeeper, lineage: ObservationLedger, *, firewall: ContextFirewall | None = None, child_runtime: ChildExecutionRuntime | None = None):
        self.gatekeeper = gatekeeper
        self.lineage = lineage
        self.firewall = firewall or ContextFirewall()
        self.child_runtime = child_runtime or ChildExecutionRuntime(gatekeeper)

    def run_skill(self, *, session_id: str, task_id: str, agent_id: str, context_items: Sequence[ContextItem], request: CapabilityRequest, execution: ExecutionRequest, explicit_approval: bool = False) -> TrustPlaneDecision:
        context = self.firewall.build(tuple(context_items), explicit_approval=explicit_approval, allowed_sensitivities=("public", "internal", "sensitive", "restricted") if explicit_approval else ("public", "internal"))
        for item in context_items:
            if item.resource_id:
                self.lineage.record(Observation(session_id, agent_id, item.resource_id, "context", item.sensitivity))
        egress = self.lineage.decide_egress(session_id, agent_id, "child:" + execution.request_id, explicit_approval=explicit_approval)
        if not egress.allowed:
            return TrustPlaneDecision(False, "lineage_egress_denied:" + egress.reason, context, egress=egress)
        try:
            gate = self.gatekeeper.prepare(request)
        except Exception as exc:
            return TrustPlaneDecision(False, "gatekeeper_denied:" + str(exc), context, egress=egress)
        if gate.status == "waiting_approval":
            if not explicit_approval:
                return TrustPlaneDecision(False, "approval_required", context, egress=egress, gate=gate)
            gate = self.gatekeeper.approve(gate.request_id)
        if gate.status != "committed":
            gate = self.gatekeeper.commit(gate.request_id)
        result = self.child_runtime.run(execution)
        return TrustPlaneDecision(result.status in {"completed"}, "child_execution:" + result.reason, context, egress=egress, gate=gate, execution=result)


__all__ = ["TrustPlane", "TrustPlaneDecision"]

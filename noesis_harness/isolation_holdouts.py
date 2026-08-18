"""Deterministic cross-agent leakage and authorization holdouts."""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Tuple

from .parallel_agent import AgentLane, SafeParallelExecutor

from .nextgen import AgentManifest, CapabilityDenied, IsolationBroker


@dataclass(frozen=True)
class IsolationHoldoutResult:
    case_id: str
    passed: bool
    observed: str
    reason: str


class ActiveDelegationLeakageSuite:
    """Run concurrent workspace escape probes while delegated lanes are active."""

    CASE_IDS: Tuple[str, ...] = ("sibling_read_denied", "sibling_write_denied", "absolute_path_denied", "traversal_denied")

    def evaluate(self) -> Tuple[IsolationHoldoutResult, ...]:
        with tempfile.TemporaryDirectory(prefix="noesis-active-leakage-") as root:
            executor = SafeParallelExecutor(root, max_concurrency=4)
            lanes = [AgentLane("agent-%d" % index, "task-%d" % index, "agent-%d" % index) for index in range(4)]
            probes = {"sibling_read_denied": "../agent-1/secret.txt", "sibling_write_denied": "../agent-2/write.txt", "absolute_path_denied": str(Path(root).parent / "outside.txt"), "traversal_denied": "../../escape.txt"}
            observed: dict[str, str] = {}

            def callback(ctx):
                case_id = tuple(probes)[int(ctx.task_id.rsplit("-", 1)[-1])]
                try:
                    ctx.path(probes[case_id])
                    observed[case_id] = "allowed"
                except Exception as exc:
                    observed[case_id] = type(exc).__name__
                return case_id

            results = executor.execute(lanes, callback, session_id="active-leakage", max_duration_seconds=5)
            return tuple(IsolationHoldoutResult(case_id, observed.get(case_id) != "allowed" and any(result.status == "passed" and result.output == case_id for result in results), observed.get(case_id, "missing"), "concurrent workspace boundary") for case_id in self.CASE_IDS)

    def pass_rate(self) -> float:
        results = self.evaluate()
        return sum(result.passed for result in results) / len(results) if results else 1.0


class CrossAgentLeakageSuite:
    """Run fixed negative/positive isolation cases against a fresh broker."""

    CASE_IDS: Tuple[str, ...] = (
        "same_tenant_message_allowed",
        "cross_tenant_message_denied",
        "recipient_only_receive",
        "private_scope_write_denied",
        "shared_scope_proposal_allowed",
        "wrong_recipient_cannot_decide",
        "unknown_sender_denied",
        "same_agent_private_write_allowed",
        "cross_tenant_proposal_denied",
        "unknown_recipient_denied",
        "proposal_decision_replay_denied",
        "unknown_sender_receive_denied",
    )

    @staticmethod
    def _broker() -> IsolationBroker:
        handle = tempfile.NamedTemporaryFile(prefix="noesis-isolation-", suffix=".db", delete=False)
        handle.close()
        broker = IsolationBroker(handle.name)
        broker.register(AgentManifest("a", "worker", "tenant-1", private_scope="private-a", readable_scopes=("shared",), writable_scopes=("shared",)))
        broker.register(AgentManifest("b", "worker", "tenant-1", private_scope="private-b", readable_scopes=("shared",), writable_scopes=("shared",)))
        broker.register(AgentManifest("c", "worker", "tenant-2", private_scope="private-c", readable_scopes=("shared",), writable_scopes=("shared",)))
        return broker

    def evaluate(self) -> Tuple[IsolationHoldoutResult, ...]:
        results = []
        broker = self._broker()

        mid = broker.send("a", "b", "task-1", {"message": "approved"})
        b_messages = broker.receive("b")
        a_messages = broker.receive("a")
        results.append(IsolationHoldoutResult("same_tenant_message_allowed", bool(mid) and len(b_messages) == 1 and not a_messages, "allowed", "recipient-only message delivery"))

        try:
            broker.send("a", "c", "task-2", {"secret": "private"})
            results.append(IsolationHoldoutResult("cross_tenant_message_denied", False, "allowed", "cross-tenant send was not denied"))
        except CapabilityDenied:
            results.append(IsolationHoldoutResult("cross_tenant_message_denied", True, "denied", "cross-tenant message blocked"))

        c_messages = broker.receive("c")
        results.append(IsolationHoldoutResult("recipient_only_receive", not c_messages and len(broker.receive("b")) == 1, "recipient_scoped" if not c_messages else "unexpected", "messages are not broadcast"))

        try:
            broker.propose_memory("a", "b", "private-b", {"leak": "no"})
            results.append(IsolationHoldoutResult("private_scope_write_denied", False, "allowed", "private scope write was not denied"))
        except CapabilityDenied:
            results.append(IsolationHoldoutResult("private_scope_write_denied", True, "denied", "private scope boundary enforced"))

        proposal = broker.propose_memory("a", "b", "shared", {"fact": "review"})
        results.append(IsolationHoldoutResult("shared_scope_proposal_allowed", bool(proposal) and len(broker.list_proposals("b")) == 1, "allowed", "explicit shared proposal recorded"))

        wrong_decision = broker.decide_proposal("a", proposal, True)
        results.append(IsolationHoldoutResult("wrong_recipient_cannot_decide", not wrong_decision and len(broker.list_proposals("b")) == 1, "denied", "only recipient can decide"))

        try:
            broker.send("unknown", "b", "task-3", {})
            results.append(IsolationHoldoutResult("unknown_sender_denied", False, "allowed", "unknown sender was not denied"))
        except CapabilityDenied:
            results.append(IsolationHoldoutResult("unknown_sender_denied", True, "denied", "unknown sender blocked"))

        private = broker.propose_memory("a", "a", "private-a", {"fact": "self"})
        results.append(IsolationHoldoutResult("same_agent_private_write_allowed", bool(private) and len(broker.list_proposals("a")) == 1, "allowed", "agent may write its own private scope"))

        try:
            broker.propose_memory("a", "c", "shared", {"fact": "cross-tenant"})
            results.append(IsolationHoldoutResult("cross_tenant_proposal_denied", False, "allowed", "cross-tenant proposal was not denied"))
        except CapabilityDenied:
            results.append(IsolationHoldoutResult("cross_tenant_proposal_denied", True, "denied", "cross-tenant proposal blocked"))

        try:
            broker.send("a", "missing", "task-4", {})
            results.append(IsolationHoldoutResult("unknown_recipient_denied", False, "allowed", "unknown recipient was not denied"))
        except CapabilityDenied:
            results.append(IsolationHoldoutResult("unknown_recipient_denied", True, "denied", "unknown recipient blocked"))

        replay_proposal = broker.propose_memory("a", "b", "shared", {"fact": "single-use"})
        first_decision = broker.decide_proposal("b", replay_proposal, True)
        replay = broker.decide_proposal("b", replay_proposal, True)
        results.append(IsolationHoldoutResult("proposal_decision_replay_denied", first_decision and not replay, "denied", "proposal decision is single-use"))

        try:
            broker.receive("missing")
            results.append(IsolationHoldoutResult("unknown_sender_receive_denied", False, "allowed", "unknown receiver was not denied"))
        except CapabilityDenied:
            results.append(IsolationHoldoutResult("unknown_sender_receive_denied", True, "denied", "unknown receiver blocked"))
        return tuple(results)

    def pass_rate(self) -> float:
        results = self.evaluate()
        return sum(1 for result in results if result.passed) / len(results) if results else 1.0


__all__ = ["CrossAgentLeakageSuite", "IsolationHoldoutResult"]

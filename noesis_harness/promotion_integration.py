"""Task/evaluator/operator integration for the governed learning pipeline."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import time
from typing import Any, Callable, Iterable, Mapping

from .event_store import EventStore
from .learning_promotion import ExperienceReceipt, HoldoutEvaluation, LearningPromotionPipeline, PromotionProposal


@dataclass(frozen=True)
class EvaluatorSpec:
    version: str
    build_cases: Callable[[ExperienceReceipt], Iterable[Mapping[str, Any]]]


class EvaluatorRegistry:
    """Explicit evaluator registry; no implicit evaluator or automatic promotion."""
    def __init__(self) -> None:
        self._items: dict[str, EvaluatorSpec] = {}

    def register(self, version: str, build_cases: Callable[[ExperienceReceipt], Iterable[Mapping[str, Any]]]) -> EvaluatorSpec:
        if not isinstance(version, str) or not version or version in self._items:
            raise ValueError("invalid_or_duplicate_evaluator_version")
        if not callable(build_cases):
            raise TypeError("evaluator_builder_required")
        spec = EvaluatorSpec(version, build_cases)
        self._items[version] = spec
        return spec

    def get(self, version: str) -> EvaluatorSpec:
        try:
            return self._items[version]
        except KeyError as exc:
            raise KeyError(f"evaluator_not_registered:{version}") from exc

    def versions(self) -> tuple[str, ...]:
        return tuple(sorted(self._items))


class PromotionTelemetry:
    """Bounded, redacted lifecycle telemetry for the operator surface."""
    def __init__(self, max_events: int = 128) -> None:
        if max_events < 1:
            raise ValueError("max_events_must_be_positive")
        self.max_events = int(max_events)
        self._events: list[dict[str, Any]] = []

    def record(self, event: str, **fields: Any) -> None:
        safe_fields = self._redact(dict(fields))
        safe = {"event": str(event), "at_epoch": int(time.time()), **safe_fields}
        self._events.append(safe)
        del self._events[:-self.max_events]

    @classmethod
    def _redact(cls, value: Any) -> Any:
        if isinstance(value, Mapping):
            secret_names = ("token", "secret", "password", "credential", "authorization", "api_key", "private_key", "content")
            return {str(k): "[REDACTED]" if any(x in str(k).casefold() for x in secret_names) else cls._redact(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [cls._redact(v) for v in value]
        return value

    def snapshot(self) -> dict[str, Any]:
        events = [dict(item) for item in self._events]
        counts: dict[str, int] = {}
        for item in events:
            counts[item["event"]] = counts.get(item["event"], 0) + 1
        return {"events": events, "counts": counts, "active_activation": False, "automatic_activation": False}


@dataclass(frozen=True)
class PolicySimulation:
    allowed: bool
    source_digest: str = ""
    policy_digest: str = ""
    agent_id: str = ""
    scope: str = ""
    payload: Any = None
    reason: str = ""


class PromotionEventBridge:
    """Replay terminal task events into promotion capture behind a policy simulator.

    The bridge is deliberately capture-only: policy denial is recorded, evaluator
    execution is never implicit, and approval/promotion remain operator actions.
    Checkpoints are append-only and retries are idempotent by task-event identity.
    """

    def __init__(self, integration: "PromotionIntegration", checkpoint_path: str) -> None:
        self.integration = integration
        self.checkpoints = EventStore(checkpoint_path)

    def _checkpoint_state(self) -> dict[str, dict[str, Any]]:
        state: dict[str, dict[str, Any]] = {}
        for event in self.checkpoints.iter_events():
            payload = event.get("payload") or {}
            event_id = str(payload.get("task_event_id", ""))
            if event_id:
                state[event_id] = dict(payload)
        return state

    def _existing_receipt(self, experience_id: str) -> ExperienceReceipt | None:
        for receipt in self.integration.pipeline._receipts.values():
            if receipt.experience_id == experience_id:
                return receipt
        return None

    def poll(self, task_store: Any, policy_simulator: Callable[[Mapping[str, Any]], Mapping[str, Any] | PolicySimulation]) -> tuple[Mapping[str, Any], ...]:
        checkpoints = self._checkpoint_state()
        outcomes: list[Mapping[str, Any]] = []
        for event in task_store.events.iter_events():
            if event.get("type") != "task_state_changed":
                continue
            payload = dict(event.get("payload") or {})
            if payload.get("state") not in {"committed", "failed", "cancelled"}:
                continue
            task_event_id = str(event.get("event_id", ""))
            if not task_event_id or checkpoints.get(task_event_id, {}).get("status") in {"completed", "denied"}:
                continue
            task = dict(payload)
            task["task_id"] = task.get("task_id", "")
            state = str(task.get("state", ""))
            if state == "cancelled":
                self.integration.telemetry.record("promotion_blocked", task_event_id=task_event_id, reason="cancelled_task")
                result = {"task_event_id": task_event_id, "status": "denied", "reason": "cancelled_task"}
                self.checkpoints.append("promotion_bridge_denied", result, event_id="bridge-denied:" + task_event_id)
                outcomes.append(result)
                continue
            task["status"] = "completed" if state == "committed" else "failed"
            self.checkpoints.append("promotion_bridge_started", {"task_event_id": task_event_id}, event_id="bridge-start:" + task_event_id)
            try:
                simulation_raw = policy_simulator(task)
                simulation = simulation_raw if isinstance(simulation_raw, PolicySimulation) else PolicySimulation(**dict(simulation_raw))
                if not simulation.allowed:
                    self.integration.telemetry.record("promotion_blocked", task_event_id=task_event_id, reason=simulation.reason or "policy_denied")
                    result = {"task_event_id": task_event_id, "status": "denied", "reason": simulation.reason or "policy_denied"}
                    self.checkpoints.append("promotion_bridge_denied", result, event_id="bridge-denied:" + task_event_id)
                    outcomes.append(result)
                    continue
                for value, field in ((simulation.source_digest, "source_digest"), (simulation.policy_digest, "policy_digest"), (simulation.agent_id, "agent_id"), (simulation.scope, "scope")):
                    if not value:
                        raise ValueError(field + "_required")
                experience_id = str(task["task_id"])
                receipt = self._existing_receipt(experience_id)
                if receipt is None:
                    receipt = self.integration.capture_task_completion(task, payload=simulation.payload, source_digest=simulation.source_digest, policy_digest=simulation.policy_digest, agent_id=simulation.agent_id, scope=simulation.scope)
                result = {"task_event_id": task_event_id, "status": "completed", "receipt_id": receipt.receipt_id}
                self.checkpoints.append("promotion_bridge_completed", result, event_id="bridge-complete:" + task_event_id)
                outcomes.append(result)
            except Exception as exc:
                self.integration.telemetry.record("promotion_blocked", task_event_id=task_event_id, reason="policy_simulation_error:" + type(exc).__name__)
                result = {"task_event_id": task_event_id, "status": "denied", "reason": "policy_simulation_error:" + type(exc).__name__}
                self.checkpoints.append("promotion_bridge_denied", result, event_id="bridge-denied:" + task_event_id)
                outcomes.append(result)
        return tuple(outcomes)


class PromotionIntegration:
    """Glue layer from task outcomes to a review-only promotion pipeline."""
    def __init__(self, pipeline: LearningPromotionPipeline, registry: EvaluatorRegistry | None = None, telemetry: PromotionTelemetry | None = None) -> None:
        self.pipeline = pipeline
        self.registry = registry or EvaluatorRegistry()
        self.telemetry = telemetry or PromotionTelemetry()

    def capture_task_completion(self, task: Mapping[str, Any], *, payload: Any, source_digest: str, policy_digest: str, agent_id: str, scope: str) -> ExperienceReceipt:
        status = str(task.get("status", ""))
        if status not in {"done", "completed", "success", "failed"}:
            raise ValueError("task_not_terminal")
        experience_id = str(task.get("task_id") or task.get("id") or "")
        if not experience_id:
            raise ValueError("task_id_required")
        receipt = self.pipeline.capture(experience_id=experience_id, agent_id=agent_id, scope=scope, source_digest=source_digest, outcome="success" if status in {"done", "completed", "success"} else "failure", payload=payload, policy_digest=policy_digest)
        self.telemetry.record("experience_captured", receipt_id=receipt.receipt_id, experience_id=receipt.experience_id, scope=scope)
        return receipt

    def evaluate(self, receipt_id: str, evaluator_version: str) -> HoldoutEvaluation:
        spec = self.registry.get(evaluator_version)
        receipt = self.pipeline._receipts.get(receipt_id)
        if receipt is None:
            raise KeyError(receipt_id)
        result = self.pipeline.evaluate(receipt_id, spec.build_cases(receipt), evaluator_version=evaluator_version)
        self.telemetry.record("holdout_evaluated", receipt_id=receipt_id, evaluation_id=result.evaluation_id, status=result.status, total_cases=result.total_cases, leaked_cases=result.leaked_cases)
        return result

    def propose(self, receipt_id: str, evaluation_id: str, *, skill_name: str, content: str) -> PromotionProposal:
        proposal = self.pipeline.propose(receipt_id, evaluation_id, skill_name=skill_name, content=content)
        self.telemetry.record("promotion_proposed", proposal_id=proposal.proposal_id, state=proposal.state, skill_name=skill_name)
        return proposal

    def approve(self, proposal_id: str, *, approved_by: str, tests: Callable[[], bool]) -> PromotionProposal:
        proposal = self.pipeline.approve(proposal_id, approved_by=approved_by, tests=tests)
        self.telemetry.record("promotion_approved", proposal_id=proposal_id, approved_by=approved_by, state=proposal.state)
        return proposal

    def promote(self, proposal_id: str, *, content: str, verify: Callable[[Any], bool], activate: bool = False) -> tuple[PromotionProposal, str]:
        proposal, signature = self.pipeline.promote(proposal_id, content=content, verify=verify, activate=activate)
        self.telemetry.record("promotion_completed", proposal_id=proposal_id, state=proposal.state, version=proposal.version, activation=activate)
        return proposal, signature

    def rollback(self, proposal_id: str) -> PromotionProposal:
        proposal = self.pipeline.rollback(proposal_id)
        self.telemetry.record("promotion_rolled_back", proposal_id=proposal_id, state=proposal.state)
        return proposal

    def snapshot(self) -> dict[str, Any]:
        return self.telemetry.snapshot()


__all__ = ["EvaluatorSpec", "EvaluatorRegistry", "PromotionTelemetry", "PolicySimulation", "PromotionEventBridge", "PromotionIntegration"]

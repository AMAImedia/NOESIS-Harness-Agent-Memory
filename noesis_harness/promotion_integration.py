"""Task/evaluator/operator integration for the governed learning pipeline."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import time
from typing import Any, Callable, Iterable, Mapping

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


__all__ = ["EvaluatorSpec", "EvaluatorRegistry", "PromotionTelemetry", "PromotionIntegration"]

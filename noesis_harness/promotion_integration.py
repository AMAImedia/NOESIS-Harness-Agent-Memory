"""Task/evaluator/operator integration for the governed learning pipeline."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import time
from typing import Any, Callable, Iterable, Mapping, Sequence

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
class RuntimePolicySimulator:
    """Deterministic runtime-owned policy decision; never performs side effects."""
    agent_id: str
    scope: str
    allowed_scopes: tuple[str, ...] = ()
    policy_version: str = "promotion-policy.v1"

    def __post_init__(self) -> None:
        if not self.agent_id or not self.scope or not self.policy_version:
            raise ValueError("runtime_policy_identity_required")
        if self.allowed_scopes and self.scope not in self.allowed_scopes:
            raise ValueError("runtime_policy_scope_not_allowed")

    def simulate(self, task: Mapping[str, Any]) -> "PolicySimulation":
        state = str(task.get("state", ""))
        if state not in {"committed", "failed"}:
            return PolicySimulation(False, agent_id=self.agent_id, scope=self.scope, reason="non_terminal_state")
        task_id = str(task.get("task_id", ""))
        if not task_id:
            return PolicySimulation(False, agent_id=self.agent_id, scope=self.scope, reason="task_id_required")
        canonical_task = json.dumps({"task_id": task_id, "state": state, "reason": str(task.get("reason", ""))}, sort_keys=True, separators=(",", ":"))
        source_digest = hashlib.sha256(canonical_task.encode("utf-8")).hexdigest()
        policy_digest = hashlib.sha256(json.dumps({"policy_version": self.policy_version, "scope": self.scope, "allowed_scopes": list(self.allowed_scopes)}, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        return PolicySimulation(True, source_digest, policy_digest, self.agent_id, self.scope, {"task_id": task_id, "state": state})


@dataclass(frozen=True)
class PromotionActionReceipt:
    action_id: str
    proposal_id: str
    action: str
    operator_id: str
    previous_state: str
    new_state: str
    signed_receipt: str
    schema_version: str = "noesis.promotion-action-receipt.v1"

    def to_mapping(self) -> dict[str, str]:
        return {"schema_version": self.schema_version, "action_id": self.action_id, "proposal_id": self.proposal_id, "action": self.action, "operator_id": self.operator_id, "previous_state": self.previous_state, "new_state": self.new_state, "signed_receipt": self.signed_receipt}


class PromotionActionExecutor:
    """Execute only explicit operator proposal actions; replay is idempotent."""

    def __init__(self, integration: "PromotionIntegration", receipt_path: str, *, approval_tests: Callable[[], bool] | None = None, independent_reviewer: Callable[[str, str], bool] | None = None, reviewer_store: ReviewerAuthorizationStore | None = None, session_registry: OperatorSessionRegistry | None = None, required_scope: str = "promotion:review") -> None:
        self.integration = integration
        self.receipts = EventStore(receipt_path)
        self.approval_tests = approval_tests or (lambda: True)
        self.independent_reviewer = independent_reviewer or (lambda operator_id, owner_id: operator_id != owner_id)
        self.reviewer_store = reviewer_store
        self.session_registry = session_registry
        self.required_scope = str(required_scope)

    def _existing(self, action_id: str) -> PromotionActionReceipt | None:
        for event in self.receipts.iter_events():
            if event.get("type") == "promotion_action_completed" and (event.get("payload") or {}).get("action_id") == action_id:
                payload = event["payload"]
                return PromotionActionReceipt(**{key: payload[key] for key in ("action_id", "proposal_id", "action", "operator_id", "previous_state", "new_state", "signed_receipt")})
        return None

    def _deny(self, action: PromotionApprovalAction | None, reason: str, error_type: type[Exception]) -> None:
        self.integration.telemetry.record("promotion_action_denied", action_id=action.action_id if action else "", proposal_id=action.proposal_id if action else "", reason=reason)
        raise error_type(reason)

    def handle(self, action: PromotionApprovalAction, auth_context: OperatorAuthContext | None = None) -> Mapping[str, Any]:
        if not isinstance(action, PromotionApprovalAction):
            raise ValueError("promotion_action_required")
        if auth_context is None:
            self._deny(action, "operator_auth_context_required", PermissionError)
        try:
            auth_context.authorize(action)
        except PermissionError as exc:
            self._deny(action, str(exc), PermissionError)
        existing = self._existing(action.action_id)
        if existing is not None:
            self.integration.telemetry.record("promotion_action_replayed", action_id=action.action_id, proposal_id=action.proposal_id)
            return {"status": "replayed", "receipt": existing.to_mapping()}
        proposal = self.integration.pipeline._proposals.get(action.proposal_id)
        if proposal is None:
            self._deny(action, "proposal_not_found", KeyError)
        if proposal.state != action.expected_state:
            self._deny(action, "proposal_state_conflict", ValueError)
        receipt = self.integration.pipeline._receipts.get(proposal.receipt_id)
        owner_id = receipt.agent_id if receipt is not None else ""
        if not owner_id or not self.independent_reviewer(action.operator_id, owner_id):
            self._deny(action, "independent_reviewer_required", PermissionError)
        if self.session_registry is not None:
            try:
                self.session_registry.require_active(auth_context)
            except PermissionError:
                self._deny(action, "operator_session_inactive_or_expired", PermissionError)
        if self.reviewer_store is not None and not self.reviewer_store.can_review(auth_context, owner_id, required_scope=self.required_scope):
            self._deny(action, "reviewer_authorization_required", PermissionError)
        previous = proposal.state
        if action.action == "approve":
            updated = self.integration.approve(action.proposal_id, approved_by=action.operator_id, tests=self.approval_tests)
        elif action.action == "reject":
            updated = self.integration.pipeline.reject(action.proposal_id, rejected_by=action.operator_id)
            self.integration.telemetry.record("promotion_rejected", proposal_id=action.proposal_id, operator_id=action.operator_id, state=updated.state)
        else:
            updated = self.integration.rollback(action.proposal_id)
        payload = {"action_id": action.action_id, "proposal_id": action.proposal_id, "action": action.action, "operator_id": action.operator_id, "previous_state": previous, "new_state": updated.state}
        signed = self.integration.pipeline._sign(payload)
        completed = PromotionActionReceipt(**{**payload, "signed_receipt": signed})
        self.receipts.append("promotion_action_completed", completed.to_mapping(), event_id="promotion-action:" + action.action_id)
        return {"status": "applied", "receipt": completed.to_mapping()}


class OwnershipPolicySimulator:
    """Derive promotion policy from authoritative task/session ownership metadata."""

    def __init__(self, task_store: Any, owner_lookup: Callable[[str], str], *, scope_prefix: str = "session:", allowed_scopes: Sequence[str] = (), policy_version: str = "promotion-policy.v2") -> None:
        if not callable(owner_lookup) or not scope_prefix or not policy_version:
            raise ValueError("ownership_policy_configuration_required")
        self.task_store = task_store
        self.owner_lookup = owner_lookup
        self.scope_prefix = scope_prefix
        self.allowed_scopes = tuple(str(item) for item in allowed_scopes)
        self.policy_version = policy_version

    def simulate(self, task: Mapping[str, Any]) -> "PolicySimulation":
        task_id = str(task.get("task_id", ""))
        event_session_id = str(task.get("session_id", ""))
        if not task_id or not event_session_id:
            return PolicySimulation(False, reason="ownership_identity_required")
        try:
            record = self.task_store.task(task_id)
            owner = str(self.owner_lookup(task_id))
        except Exception as exc:
            return PolicySimulation(False, reason="ownership_lookup_failed:" + type(exc).__name__)
        if record.session_id != event_session_id:
            return PolicySimulation(False, reason="ownership_session_mismatch")
        if not owner:
            return PolicySimulation(False, reason="task_owner_missing")
        scope = self.scope_prefix + record.session_id
        if self.allowed_scopes and scope not in self.allowed_scopes:
            return PolicySimulation(False, agent_id=owner, scope=scope, reason="ownership_scope_denied")
        runtime = RuntimePolicySimulator(owner, scope, allowed_scopes=(scope,), policy_version=self.policy_version)
        return runtime.simulate({**dict(task), "state": task.get("state", "")})


class OperatorSessionRegistry:
    """Persistent operator session state with expiry and fail-closed validation."""

    def __init__(self, event_path: str, *, clock: Callable[[], float] = time.time) -> None:
        self.events = EventStore(event_path)
        self.clock = clock

    def open(self, operator_id: str, session_id: str, *, ttl_seconds: float = 900.0, scopes: Sequence[str] = ()) -> Mapping[str, Any]:
        if not operator_id or not session_id or ttl_seconds <= 0 or ttl_seconds > 86400:
            raise ValueError("invalid_operator_session")
        now = float(self.clock())
        payload = {"operator_id": str(operator_id), "session_id": str(session_id), "scopes": sorted({str(item) for item in scopes}), "opened_at": now, "expires_at": now + float(ttl_seconds), "active": True}
        self.events.append("operator_session_opened", payload, event_id="operator-session-open:" + session_id + ":" + str(self.events.count()))
        return payload

    def close(self, operator_id: str, session_id: str, *, reason: str = "closed") -> Mapping[str, Any]:
        if not operator_id or not session_id:
            raise ValueError("invalid_operator_session")
        payload = {"operator_id": str(operator_id), "session_id": str(session_id), "active": False, "reason": str(reason)[:128], "closed_at": float(self.clock())}
        self.events.append("operator_session_closed", payload, event_id="operator-session-close:" + session_id + ":" + str(self.events.count()))
        return payload

    def _records(self) -> dict[str, Mapping[str, Any]]:
        state: dict[str, Mapping[str, Any]] = {}
        for event in self.events.iter_events():
            payload = event.get("payload") or {}
            sid = str(payload.get("session_id", ""))
            if sid:
                previous = dict(state.get(sid, {}))
                previous.update(payload)
                state[sid] = previous
        return state

    def context(self, operator_id: str, session_id: str) -> "OperatorAuthContext":
        record = self._records().get(str(session_id))
        now = float(self.clock())
        if not record or record.get("operator_id") != str(operator_id) or not record.get("active", False) or float(record.get("expires_at", 0.0)) <= now:
            return OperatorAuthContext(str(operator_id), str(session_id), (), authenticated=False)
        return OperatorAuthContext(str(operator_id), str(session_id), tuple(str(item) for item in record.get("scopes", ())), authenticated=True)

    def require_active(self, context: "OperatorAuthContext") -> None:
        current = self.context(context.operator_id, context.session_id)
        if not current.authenticated or current.scopes != context.scopes:
            raise PermissionError("operator_session_inactive_or_expired")


class ReviewerAuthorizationStore:
    """Append-only operator reviewer grants; absence or revocation fails closed."""

    def __init__(self, event_path: str) -> None:
        self.events = EventStore(event_path)

    def grant(self, operator_id: str, session_id: str, scopes: Sequence[str] = ()) -> Mapping[str, Any]:
        if not operator_id or not session_id:
            raise ValueError("reviewer_identity_required")
        payload = {"operator_id": str(operator_id), "session_id": str(session_id), "scopes": sorted({str(item) for item in scopes}), "active": True}
        self.events.append("reviewer_granted", payload, event_id="reviewer-grant:" + operator_id + ":" + session_id)
        return payload

    def revoke(self, operator_id: str, session_id: str) -> Mapping[str, Any]:
        if not operator_id or not session_id:
            raise ValueError("reviewer_identity_required")
        payload = {"operator_id": str(operator_id), "session_id": str(session_id), "active": False}
        self.events.append("reviewer_revoked", payload, event_id="reviewer-revoke:" + operator_id + ":" + session_id + ":" + str(self.events.count()))
        return payload

    def _records(self) -> dict[tuple[str, str], Mapping[str, Any]]:
        state: dict[tuple[str, str], Mapping[str, Any]] = {}
        for event in self.events.iter_events():
            payload = event.get("payload") or {}
            key = (str(payload.get("operator_id", "")), str(payload.get("session_id", "")))
            if key[0] and key[1]:
                state[key] = dict(payload)
        return state

    def authorize(self, context: "OperatorAuthContext", *, required_scope: str = "") -> None:
        record = self._records().get((context.operator_id, context.session_id))
        if not context.authenticated or record is None or not record.get("active", False):
            raise PermissionError("reviewer_authorization_required")
        granted = set(str(item) for item in record.get("scopes", ()))
        if required_scope and required_scope not in granted:
            raise PermissionError("reviewer_scope_denied")
        if required_scope and required_scope not in context.scopes:
            raise PermissionError("operator_scope_denied")

    def can_review(self, context: "OperatorAuthContext", owner_id: str, *, required_scope: str = "") -> bool:
        if context.operator_id == owner_id:
            return False
        try:
            self.authorize(context, required_scope=required_scope)
        except PermissionError:
            return False
        return True


@dataclass(frozen=True)
class OperatorAuthContext:
    operator_id: str
    session_id: str
    scopes: tuple[str, ...] = ()
    authenticated: bool = True

    def authorize(self, action: "PromotionApprovalAction") -> None:
        if not self.authenticated or not self.operator_id or self.operator_id != action.operator_id:
            raise PermissionError("operator_identity_mismatch")
        if action.session_id and self.session_id != action.session_id:
            raise PermissionError("operator_session_mismatch")
        if action.scope and action.scope not in self.scopes:
            raise PermissionError("operator_scope_denied")


@dataclass(frozen=True)
class PromotionApprovalAction:
    """Versioned, non-secret operator action; handler decides side effects explicitly."""
    action_id: str
    action: str
    proposal_id: str
    operator_id: str
    expected_state: str = "review"
    session_id: str = ""
    scope: str = ""
    schema_version: str = "noesis.promotion-approval.v1"

    def __post_init__(self) -> None:
        if not self.action_id or not self.proposal_id or not self.operator_id:
            raise ValueError("approval_action_identity_required")
        if self.action not in {"approve", "reject", "rollback"}:
            raise ValueError("unsupported_approval_action")
        if self.expected_state not in {"review", "approved", "promoted"}:
            raise ValueError("unsupported_expected_state")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PromotionApprovalAction":
        if not isinstance(value, Mapping) or value.get("schema_version") != "noesis.promotion-approval.v1":
            raise ValueError("unsupported_approval_action_schema")
        return cls(str(value.get("action_id", "")), str(value.get("action", "")), str(value.get("proposal_id", "")), str(value.get("operator_id", "")), str(value.get("expected_state", "review")), str(value.get("session_id", "")), str(value.get("scope", "")))

    def to_mapping(self) -> dict[str, str]:
        return {"schema_version": self.schema_version, "action_id": self.action_id, "action": self.action, "proposal_id": self.proposal_id, "operator_id": self.operator_id, "expected_state": self.expected_state, "session_id": self.session_id, "scope": self.scope}


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


__all__ = ["EvaluatorSpec", "EvaluatorRegistry", "PromotionTelemetry", "RuntimePolicySimulator", "OwnershipPolicySimulator", "OperatorSessionRegistry", "ReviewerAuthorizationStore", "OperatorAuthContext", "PromotionApprovalAction", "PromotionActionReceipt", "PromotionActionExecutor", "PolicySimulation", "PromotionEventBridge", "PromotionIntegration"]

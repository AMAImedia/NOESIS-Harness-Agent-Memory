"""Task/evaluator/operator integration for the governed learning pipeline."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import hmac
import json
import time
from typing import Any, Callable, Iterable, Mapping, Sequence

from .event_store import EventStore
from .learning_corpus_binding import LearningCorpusBindingError, attach_to_telemetry, verify_corpus_binding
from .learning_promotion import DurablePromotionState, ExperienceReceipt, HoldoutEvaluation, LearningPromotionPipeline, PromotionProposal, _digest


@dataclass(frozen=True)
class EvaluatorSpec:
    version: str
    build_cases: Callable[[ExperienceReceipt], Iterable[Mapping[str, Any]]]


class EvaluatorRegistry:
    """Explicit evaluator registry; no implicit evaluator or automatic promotion."""
    def __init__(self, *, state: DurablePromotionState | None = None) -> None:
        self._items: dict[str, EvaluatorSpec] = {}
        self._manifest_digests: dict[str, str] = {}
        self._state = state

    def register(self, version: str, build_cases: Callable[[ExperienceReceipt], Iterable[Mapping[str, Any]]], *, manifest_digest: str | None = None) -> EvaluatorSpec:
        if not isinstance(version, str) or not version or version in self._items:
            raise ValueError("invalid_or_duplicate_evaluator_version")
        if not callable(build_cases):
            raise TypeError("evaluator_builder_required")
        digest = manifest_digest or self._manifest_digest(version, build_cases)
        if not isinstance(digest, str) or not digest:
            raise ValueError("evaluator_manifest_digest_required")
        if self._state is not None:
            self._state.register_evaluator(version, digest)
        spec = EvaluatorSpec(version, build_cases)
        self._items[version] = spec
        self._manifest_digests[version] = digest
        return spec

    @staticmethod
    def _manifest_digest(version: str, builder: Callable[[ExperienceReceipt], Iterable[Mapping[str, Any]]]) -> str:
        return _digest({"version": version, "builder": getattr(builder, "__qualname__", type(builder).__name__)})

    def manifests(self) -> Mapping[str, str]:
        if self._state is not None:
            return dict(self._state.evaluator_manifests())
        return {version: self._manifest_digests.get(version, self._manifest_digest(version, spec.build_cases)) for version, spec in sorted(self._items.items())}

    def readiness(self) -> Mapping[str, Any]:
        persisted = dict(self._state.evaluator_manifests()) if self._state is not None else {}
        registered = {version: self._manifest_digests.get(version, self._manifest_digest(version, spec.build_cases)) for version, spec in sorted(self._items.items())}
        missing_runtime = sorted(set(persisted) - set(registered))
        manifest_conflicts = sorted(version for version in set(persisted) & set(registered) if persisted[version] != registered[version])
        if missing_runtime or manifest_conflicts:
            status = "blocked"
        elif registered:
            status = "ready"
        else:
            status = "not_configured"
        return {
            "schema_version": "noesis.evaluator-readiness.v1",
            "status": status,
            "registered_versions": sorted(registered),
            "persisted_versions": sorted(persisted),
            "missing_runtime_versions": missing_runtime,
            "manifest_conflicts": manifest_conflicts,
            "runtime_available": status == "ready",
            "automatic_registration": False,
        }

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
            if all(existing.to_mapping().get(key) == action.to_mapping().get(key) for key in ("action_id", "proposal_id", "action", "operator_id")):
                self.integration.telemetry.record("promotion_action_replayed", action_id=action.action_id, proposal_id=action.proposal_id)
                return {"status": "replayed", "receipt": existing.to_mapping()}
            self._deny(action, "promotion_action_replay_conflict", PermissionError)
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
        requested_scopes = sorted({str(item) for item in scopes})
        existing = self._records().get(str(session_id))
        if existing is not None:
            if existing.get("operator_id") == str(operator_id) and existing.get("active", False) and sorted(str(item) for item in existing.get("scopes", ())) == requested_scopes:
                return dict(existing)
            raise ValueError("operator_session_conflict")
        now = float(self.clock())
        payload = {"operator_id": str(operator_id), "session_id": str(session_id), "scopes": requested_scopes, "opened_at": now, "expires_at": now + float(ttl_seconds), "active": True}
        self.events.append("operator_session_opened", payload, event_id="operator-session-open:" + session_id)
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
        normalized_scopes = sorted({str(item) for item in scopes})
        payload = {"operator_id": str(operator_id), "session_id": str(session_id), "scopes": normalized_scopes, "active": True}
        scope_digest = hashlib.sha256(json.dumps(normalized_scopes, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
        self.events.append("reviewer_granted", payload, event_id="reviewer-grant:" + operator_id + ":" + session_id + ":" + scope_digest)
        return payload

    def revoke(self, operator_id: str, session_id: str) -> Mapping[str, Any]:
        if not operator_id or not session_id:
            raise ValueError("reviewer_identity_required")
        existing = self._records().get((str(operator_id), str(session_id)))
        if existing is not None and not existing.get("active", False):
            return dict(existing)
        payload = {"operator_id": str(operator_id), "session_id": str(session_id), "active": False}
        self.events.append("reviewer_revoked", payload, event_id="reviewer-revoke:" + operator_id + ":" + session_id)
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

    def propose(self, receipt_id: str, evaluation_id: str, *, skill_name: str, content: str, corpus_binding: Mapping[str, Any] | None = None) -> PromotionProposal:
        # Gate 1: optional evidence-corpus provenance binding. Verified
        # fail-closed BEFORE the pipeline side effect; attached additively to
        # the promotion_proposed telemetry payload; existing key would raise.
        if corpus_binding is not None and not verify_corpus_binding(corpus_binding):
            raise LearningCorpusBindingError("binding_verification_failed")
        proposal = self.pipeline.propose(receipt_id, evaluation_id, skill_name=skill_name, content=content)
        fields: dict[str, Any] = {"proposal_id": proposal.proposal_id, "state": proposal.state, "skill_name": skill_name}
        if corpus_binding is not None:
            attach_to_telemetry(fields, corpus_binding)
        self.telemetry.record("promotion_proposed", **fields)
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

    def review_snapshot(self, *, max_proposals: int = 64) -> dict[str, Any]:
        """Expose bounded proposal/evaluator metadata without skill or payload content."""
        snapshot = self.pipeline.review_snapshot(max_proposals=max_proposals)
        snapshot["evaluator_readiness"] = dict(self.registry.readiness())
        snapshot["operator_review_required"] = True
        snapshot["automatic_activation"] = False
        return snapshot

    def snapshot(self) -> dict[str, Any]:
        snapshot = self.telemetry.snapshot()
        snapshot["promotion_state"] = {"receipts": len(self.pipeline._receipts), "evaluations": len(self.pipeline._evaluations), "proposals": len(self.pipeline._proposals), "active_versions": sum(1 for name in {proposal.skill_name for proposal in self.pipeline._proposals.values()} if self.pipeline.active_version(name))}
        snapshot["evaluator_manifests"] = dict(self.registry.manifests())
        snapshot["evaluator_readiness"] = self.registry.readiness()
        return snapshot


class ProductionLearningLifecycle:
    """Bind durable task capture and explicit operator actions without implicit promotion."""

    def __init__(self, *, task_store: Any, event_bridge: PromotionEventBridge, policy_simulator: Callable[[Mapping[str, Any]], Mapping[str, Any] | PolicySimulation], action_executor: PromotionActionExecutor) -> None:
        if task_store is None or not isinstance(event_bridge, PromotionEventBridge) or not callable(policy_simulator) or not isinstance(action_executor, PromotionActionExecutor):
            raise ValueError("production_learning_lifecycle_configuration_required")
        self.task_store = task_store
        self.event_bridge = event_bridge
        self.policy_simulator = policy_simulator
        self.action_executor = action_executor

    def capture_terminal_events(self, *, operator_trigger: bool = False) -> tuple[Mapping[str, Any], ...]:
        """Capture terminal task events only after an explicit operator lifecycle trigger."""
        if not operator_trigger:
            raise PermissionError("operator_trigger_required")
        return self.event_bridge.poll(self.task_store, self.policy_simulator)

    def handle_operator_action(self, action: PromotionApprovalAction, context: OperatorAuthContext) -> Mapping[str, Any]:
        """Apply only a validated, authenticated, independently reviewed action."""
        return self.action_executor.handle(action, context)

    def readiness(self) -> Mapping[str, Any]:
        return {"schema_version": "noesis.production-learning-lifecycle.v1", "capture": "operator_trigger_only", "automatic_evaluation": False, "automatic_approval": False, "automatic_promotion": False, "automatic_activation": False, "operator_action_handler": True}


@dataclass(frozen=True)
class SignedMutationReceipt:
    action_id: str
    operation: str
    actor_id: str
    target_id: str
    previous_state: str
    new_state: str
    payload_digest: str
    signature: str
    schema_version: str = "noesis.signed-mutation-receipt.v1"

    def unsigned(self) -> dict[str, str]:
        return {"schema_version": self.schema_version, "action_id": self.action_id, "operation": self.operation, "actor_id": self.actor_id, "target_id": self.target_id, "previous_state": self.previous_state, "new_state": self.new_state, "payload_digest": self.payload_digest}

    def to_mapping(self) -> dict[str, str]:
        return {**self.unsigned(), "signature": self.signature}


def verify_signed_mutation_receipt(receipt: Mapping[str, Any] | SignedMutationReceipt, signing_key: bytes) -> bool:
    if not isinstance(signing_key, bytes) or len(signing_key) < 16:
        return False
    data = receipt.to_mapping() if isinstance(receipt, SignedMutationReceipt) else dict(receipt)
    unsigned = {key: data.get(key, "") for key in ("schema_version", "action_id", "operation", "actor_id", "target_id", "previous_state", "new_state", "payload_digest")}
    expected = hmac.new(signing_key, json.dumps(unsigned, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), hashlib.sha256).hexdigest()
    return data.get("schema_version") == "noesis.signed-mutation-receipt.v1" and isinstance(data.get("signature"), str) and hmac.compare_digest(expected, data["signature"])


def _signed_mutation_receipt(signing_key: bytes, *, action_id: str, operation: str, actor_id: str, target_id: str, previous_state: str, new_state: str, payload: Mapping[str, Any]) -> SignedMutationReceipt:
    if not isinstance(signing_key, bytes) or len(signing_key) < 16:
        raise ValueError("signing_key_too_short")
    payload_digest = hashlib.sha256(json.dumps(dict(payload), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
    unsigned = {"schema_version": "noesis.signed-mutation-receipt.v1", "action_id": action_id, "operation": operation, "actor_id": actor_id, "target_id": target_id, "previous_state": previous_state, "new_state": new_state, "payload_digest": payload_digest}
    signature = hmac.new(signing_key, json.dumps(unsigned, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), hashlib.sha256).hexdigest()
    return SignedMutationReceipt(action_id, operation, actor_id, target_id, previous_state, new_state, payload_digest, signature)


class CoordinatedMutationJournal:
    """Durable prepare/commit journal coordinating state and audit stores.

    The journal does not pretend to provide cross-file atomicity: an uncommitted
    prepared mutation is surfaced as incomplete and cannot be auto-promoted.
    """

    def __init__(self, path: str) -> None:
        self.events = EventStore(path)

    def prepare(self, action_id: str, operation: str, target_id: str, receipt: Mapping[str, Any]) -> None:
        if not action_id or not operation or not target_id or not isinstance(receipt, Mapping):
            raise ValueError("mutation_journal_identity_required")
        existing = self._prepared_record(action_id)
        requested = {"action_id": str(action_id), "operation": str(operation), "target_id": str(target_id), "receipt": dict(receipt)}
        if existing is not None:
            if json.dumps(existing, sort_keys=True, ensure_ascii=False, separators=(",", ":")) == json.dumps(requested, sort_keys=True, ensure_ascii=False, separators=(",", ":")):
                return
            raise ValueError("mutation_prepare_conflict")
        if self.status(action_id) in {"committed", "aborted"}:
            raise ValueError("mutation_terminal_conflict")
        self.events.append("mutation_prepared", requested, event_id="mutation-prepare:" + action_id)

    def commit(self, action_id: str) -> None:
        if self.status(action_id) == "committed":
            return
        if self.status(action_id) != "incomplete":
            raise ValueError("mutation_commit_requires_prepare")
        self.events.append("mutation_committed", {"action_id": action_id}, event_id="mutation-commit:" + action_id)

    def abort(self, action_id: str, reason: str) -> None:
        if self.status(action_id) == "aborted":
            return
        if self.status(action_id) != "incomplete":
            raise ValueError("mutation_abort_requires_prepare")
        self.events.append("mutation_aborted", {"action_id": action_id, "reason": str(reason)[:128]}, event_id="mutation-abort:" + action_id)

    def _prepared_record(self, action_id: str) -> Mapping[str, Any] | None:
        for event in self.events.iter_events():
            payload = event.get("payload") or {}
            if event.get("type") == "mutation_prepared" and payload.get("action_id") == action_id:
                return dict(payload)
        return None

    def status(self, action_id: str) -> str:
        prepared = committed = aborted = False
        for event in self.events.iter_events():
            payload = event.get("payload") or {}
            if payload.get("action_id") != action_id:
                continue
            prepared |= event.get("type") == "mutation_prepared"
            committed |= event.get("type") == "mutation_committed"
            aborted |= event.get("type") == "mutation_aborted"
        if committed:
            return "committed"
        if aborted:
            return "aborted"
        if prepared:
            return "incomplete"
        return "unknown"

    def incomplete(self) -> tuple[Mapping[str, Any], ...]:
        prepared: dict[str, Mapping[str, Any]] = {}
        terminal: set[str] = set()
        for event in self.events.iter_events():
            payload = event.get("payload") or {}
            action_id = str(payload.get("action_id", ""))
            if not action_id:
                continue
            if event.get("type") == "mutation_prepared":
                prepared[action_id] = dict(payload)
            elif event.get("type") in {"mutation_committed", "mutation_aborted"}:
                terminal.add(action_id)
        return tuple(prepared[action_id] for action_id in sorted(prepared) if action_id not in terminal)


@dataclass(frozen=True)
class OperatorSessionAction:
    action_id: str
    action: str
    operator_id: str
    session_id: str
    ttl_seconds: float = 900.0
    scopes: tuple[str, ...] = ()
    schema_version: str = "noesis.operator-session-action.v1"

    def __post_init__(self) -> None:
        if not self.action_id or not self.operator_id or not self.session_id:
            raise ValueError("operator_session_action_identity_required")
        if self.action not in {"open", "close"}:
            raise ValueError("unsupported_operator_session_action")
        if self.action == "open" and (self.ttl_seconds <= 0 or self.ttl_seconds > 86400):
            raise ValueError("invalid_operator_session_ttl")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "OperatorSessionAction":
        if not isinstance(value, Mapping) or value.get("schema_version") != "noesis.operator-session-action.v1":
            raise ValueError("unsupported_operator_session_action_schema")
        return cls(str(value.get("action_id", "")), str(value.get("action", "")), str(value.get("operator_id", "")), str(value.get("session_id", "")), float(value.get("ttl_seconds", 900.0)), tuple(str(item) for item in value.get("scopes", ())))

    def to_mapping(self) -> dict[str, Any]:
        return {"schema_version": self.schema_version, "action_id": self.action_id, "action": self.action, "operator_id": self.operator_id, "session_id": self.session_id, "ttl_seconds": self.ttl_seconds, "scopes": list(self.scopes)}


class AdministrativePolicyStore:
    """Reviewed administrative source for reviewer grants and revocations."""

    def __init__(self, event_path: str, reviewer_store: ReviewerAuthorizationStore, session_registry: OperatorSessionRegistry, *, admin_ids: Sequence[str], signing_key: bytes, required_scope: str = "admin:reviewers", journal: CoordinatedMutationJournal | None = None) -> None:
        if not admin_ids or not required_scope or not isinstance(signing_key, bytes) or len(signing_key) < 16:
            raise ValueError("administrative_policy_configuration_required")
        self.events = EventStore(event_path)
        self.reviewer_store = reviewer_store
        self.session_registry = session_registry
        self.admin_ids = frozenset(str(item) for item in admin_ids)
        self.signing_key = signing_key
        self.required_scope = str(required_scope)
        self.journal = journal

    def _require_admin(self, context: OperatorAuthContext) -> None:
        self.session_registry.require_active(context)
        if context.operator_id not in self.admin_ids or self.required_scope not in context.scopes:
            raise PermissionError("administrative_policy_denied")

    def grant_reviewer(self, context: OperatorAuthContext, operator_id: str, session_id: str, scopes: Sequence[str]) -> Mapping[str, Any]:
        self._require_admin(context)
        current = self.reviewer_store._records().get((str(operator_id), str(session_id)))
        normalized_scopes = sorted({str(item) for item in scopes})
        if current and current.get("active", False) and sorted(str(item) for item in current.get("scopes", ())) == normalized_scopes:
            raise PermissionError("administrative_policy_conflict")
        previous = "active" if current and current.get("active", False) else "inactive"
        preview = {"operator_id": operator_id, "session_id": session_id, "scopes": normalized_scopes, "active": True}
        receipt = _signed_mutation_receipt(self.signing_key, action_id="grant:" + operator_id + ":" + session_id + ":" + str(self.events.count()), operation="grant_reviewer", actor_id=context.operator_id, target_id=operator_id + ":" + session_id, previous_state=previous, new_state="active", payload=preview)
        if self.journal is not None:
            self.journal.prepare(receipt.action_id, "grant_reviewer", operator_id + ":" + session_id, receipt.to_mapping())
        try:
            grant = self.reviewer_store.grant(operator_id, session_id, normalized_scopes)
            payload = {"requester_id": context.operator_id, "operation": "grant_reviewer", **dict(grant), "audit_receipt": receipt.to_mapping()}
            self.events.append("administrative_policy_changed", payload, event_id="admin-policy:grant:" + operator_id + ":" + session_id + ":" + str(self.events.count()))
            if self.journal is not None:
                self.journal.commit(receipt.action_id)
        except Exception as exc:
            if self.journal is not None:
                self.journal.abort(receipt.action_id, type(exc).__name__)
            raise
        return payload

    def revoke_reviewer(self, context: OperatorAuthContext, operator_id: str, session_id: str) -> Mapping[str, Any]:
        self._require_admin(context)
        current = self.reviewer_store._records().get((str(operator_id), str(session_id)))
        if not current or not current.get("active", False):
            raise PermissionError("administrative_policy_conflict")
        preview = {"operator_id": operator_id, "session_id": session_id, "active": False}
        receipt = _signed_mutation_receipt(self.signing_key, action_id="revoke:" + operator_id + ":" + session_id + ":" + str(self.events.count()), operation="revoke_reviewer", actor_id=context.operator_id, target_id=operator_id + ":" + session_id, previous_state="active", new_state="inactive", payload=preview)
        if self.journal is not None:
            self.journal.prepare(receipt.action_id, "revoke_reviewer", operator_id + ":" + session_id, receipt.to_mapping())
        try:
            revoked = self.reviewer_store.revoke(operator_id, session_id)
            payload = {"requester_id": context.operator_id, "operation": "revoke_reviewer", **dict(revoked), "audit_receipt": receipt.to_mapping()}
            self.events.append("administrative_policy_changed", payload, event_id="admin-policy:revoke:" + operator_id + ":" + session_id + ":" + str(self.events.count()))
            if self.journal is not None:
                self.journal.commit(receipt.action_id)
        except Exception as exc:
            if self.journal is not None:
                self.journal.abort(receipt.action_id, type(exc).__name__)
            raise
        return payload


class OperatorSessionActionExecutor:
    """Apply explicit open/close session actions with idempotent replay."""

    def __init__(self, registry: OperatorSessionRegistry, event_path: str, *, signing_key: bytes, journal: CoordinatedMutationJournal | None = None) -> None:
        if not isinstance(signing_key, bytes) or len(signing_key) < 16:
            raise ValueError("signing_key_too_short")
        self.registry = registry
        self.events = EventStore(event_path)
        self.signing_key = signing_key
        self.journal = journal

    def _existing(self, action_id: str) -> Mapping[str, Any] | None:
        for event in self.events.iter_events():
            payload = event.get("payload") or {}
            if event.get("type") == "operator_session_action_completed" and payload.get("action_id") == action_id:
                return dict(payload)
        return None

    def handle(self, action: OperatorSessionAction, context: OperatorAuthContext) -> Mapping[str, Any]:
        if not isinstance(action, OperatorSessionAction) or not isinstance(context, OperatorAuthContext):
            raise ValueError("operator_session_action_required")
        if context.operator_id != action.operator_id or not context.authenticated:
            raise PermissionError("operator_identity_mismatch")
        existing = self._existing(action.action_id)
        if existing is not None:
            if all(existing.get(key) == action.to_mapping().get(key) for key in ("action_id", "action", "operator_id", "session_id", "ttl_seconds", "scopes")):
                return {"status": "replayed", "result": existing}
            raise PermissionError("operator_session_action_replay_conflict")
        current = self.registry.context(action.operator_id, action.session_id)
        if action.action == "open":
            if current.authenticated:
                raise PermissionError("operator_session_conflict")
            previous_state, new_state = "inactive", "active"
        else:
            if not current.authenticated:
                raise PermissionError("operator_session_conflict")
            previous_state, new_state = "active", "inactive"
        preview = {"operator_id": action.operator_id, "session_id": action.session_id, "action": action.action, "scopes": list(action.scopes), "ttl_seconds": action.ttl_seconds}
        receipt = _signed_mutation_receipt(self.signing_key, action_id=action.action_id, operation="operator_session_" + action.action, actor_id=context.operator_id, target_id=action.session_id, previous_state=previous_state, new_state=new_state, payload=preview)
        if self.journal is not None:
            self.journal.prepare(action.action_id, "operator_session_" + action.action, action.session_id, receipt.to_mapping())
        try:
            if action.action == "open":
                result = self.registry.open(action.operator_id, action.session_id, ttl_seconds=action.ttl_seconds, scopes=action.scopes)
            else:
                result = self.registry.close(action.operator_id, action.session_id)
            payload = {"action_id": action.action_id, **action.to_mapping(), "result": dict(result), "audit_receipt": receipt.to_mapping()}
            self.events.append("operator_session_action_completed", payload, event_id="operator-session-action:" + action.action_id)
            if self.journal is not None:
                self.journal.commit(action.action_id)
        except Exception as exc:
            if self.journal is not None:
                self.journal.abort(action.action_id, type(exc).__name__)
            raise
        return {"status": "applied", "result": payload}


__all__ = [
"EvaluatorSpec", "EvaluatorRegistry", "PromotionTelemetry", "RuntimePolicySimulator", "OwnershipPolicySimulator", "OperatorSessionRegistry", "ReviewerAuthorizationStore", "OperatorAuthContext", "PromotionApprovalAction", "PromotionActionReceipt", "PromotionActionExecutor", "SignedMutationReceipt", "verify_signed_mutation_receipt", "CoordinatedMutationJournal", "OperatorSessionAction", "OperatorSessionActionExecutor", "AdministrativePolicyStore", "PolicySimulation", "PromotionEventBridge", "PromotionIntegration", "ProductionLearningLifecycle"]

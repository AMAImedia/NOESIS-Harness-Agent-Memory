"""Approval-gated bridge from durable task sessions to safe parallel lanes.

The bridge only coordinates injected callbacks. It never invokes a model,
shell command, tool, or executable skill. Those operations remain behind the
Trust Plane and ChildExecutionRuntime boundaries.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from .promotion_integration import PolicySimulation, PromotionEventBridge

from .coordination import Actions
from .parallel_agent import AgentLane, AgentLaneContext, AgentLaneResult, ParallelExecutionError, SafeParallelExecutor
from .task_session_api import TaskSessionError, TaskSessionStore
from .delegated_resume import DelegatedResumeError, DelegatedResumeStore


class TaskExecutionBridgeError(ValueError):
    """Raised when a task is not ready for approved execution."""


@dataclass(frozen=True)
class TaskExecutionRequest:
    task_id: str
    agent_id: str
    workspace: str
    capabilities: tuple[str, ...] = ("read", "provenance")


@dataclass(frozen=True)
class TaskExecutionReport:
    session_id: str
    results: tuple[AgentLaneResult, ...]


class TaskExecutionBridge:
    """Connect versioned task state with Actions and safe parallel callbacks."""

    def __init__(self, tasks: TaskSessionStore, actions: Actions, executor: SafeParallelExecutor, *, promotion_bridge: PromotionEventBridge | None = None, policy_simulator: Callable[[Mapping[str, Any]], Mapping[str, Any] | PolicySimulation] | None = None, delegated_resume_store: DelegatedResumeStore | None = None):
        self.tasks = tasks
        self.actions = actions
        self.executor = executor
        self.promotion_bridge = promotion_bridge
        self.policy_simulator = policy_simulator
        self.delegated_resume_store = delegated_resume_store

    def poll_promotion_events(self, *, operator_trigger: bool = False) -> tuple[Mapping[str, Any], ...]:
        """Poll promotion capture only after an explicit operator lifecycle trigger."""
        if not operator_trigger:
            raise TaskExecutionBridgeError("explicit_promotion_poll_trigger_required")
        if self.promotion_bridge is None or self.policy_simulator is None:
            raise TaskExecutionBridgeError("promotion_runtime_not_configured")
        return self.promotion_bridge.poll(self.tasks, self.policy_simulator)

    def register_action(self, task_id: str, title: str, *, requires: Sequence[str] = ()) -> str:
        """Create an action using the durable task ID as its stable identity."""
        return self.actions.create(title, requires=list(requires), action_id=task_id)

    def execute(
        self,
        session_id: str,
        requests: Sequence[TaskExecutionRequest],
        callback: Callable[[AgentLaneContext], object],
        *,
        approval: bool = False,
        event_sink: Optional[Callable[[Mapping[str, object]], None]] = None,
        lease_store: object | None = None,
        cancellation: object | None = None,
        max_duration_seconds: float | None = None,
        retry_limit: int = 0,
    ) -> TaskExecutionReport:
        if not approval:
            raise TaskExecutionBridgeError("explicit_execution_approval_required")
        if not requests:
            raise TaskExecutionBridgeError("execution_requests_required")
        lanes: list[AgentLane] = []
        for request in requests:
            try:
                task = self.tasks.task(request.task_id)
            except TaskSessionError as exc:
                raise TaskExecutionBridgeError("unknown_task") from exc
            if task.session_id != session_id:
                raise TaskExecutionBridgeError("task_session_mismatch")
            if task.state != "waiting_approval":
                raise TaskExecutionBridgeError("task_not_waiting_approval:%s" % task.state)
            lanes.append(AgentLane(request.agent_id, request.task_id, request.workspace, request.capabilities, True, True))

        def run_task(context: AgentLaneContext) -> object:
            self.tasks.transition_task(context.task_id, "executing", reason="approved_execution:%s" % context.agent_id)
            return callback(context)

        try:
            results = self.executor.execute(
                lanes,
                run_task,
                session_id=session_id,
                approval=True,
                action_store=self.actions,
                event_sink=event_sink,
                lease_store=lease_store,
                cancellation=cancellation,
                max_duration_seconds=max_duration_seconds,
                retry_limit=retry_limit,
            )
        except ParallelExecutionError as exc:
            raise TaskExecutionBridgeError(str(exc)) from exc

        for result in results:
            try:
                task = self.tasks.task(result.task_id)
                if result.status == "passed" and isinstance(result.output, Mapping) and isinstance(result.output.get("execution"), Mapping):
                    execution = result.output["execution"]
                    self.tasks.record_execution_evidence(session_id, result.task_id, execution, command_id="lane-execution-evidence-%s-%s" % (result.task_id, execution.get("receipt_id", "")))
                if result.status == "passed" and task.state == "executing":
                    updated = self.tasks.transition_task(result.task_id, "review", reason="parallel_lane_completed:%s" % result.agent_id)
                    kind = "task_review_ready"
                elif result.status == "failed" and task.state == "executing":
                    updated = self.tasks.transition_task(result.task_id, "failed", reason="parallel_lane_failed:%s" % result.agent_id)
                    kind = "task_failed"
                else:
                    updated = task
                    kind = "task_blocked"
                if event_sink is not None:
                    event_sink({"kind": kind, "session_id": session_id, "task_id": result.task_id, "agent_id": result.agent_id, "state": updated.state})
            except TaskSessionError as exc:
                raise TaskExecutionBridgeError("task_state_update_failed") from exc
        return TaskExecutionReport(session_id, tuple(results))

    @staticmethod
    def _runtime_evidence(runtime: Any, result: Any) -> Mapping[str, Any]:
        if getattr(result, "status", "") != "completed":
            raise ParallelExecutionError("runtime_execution_not_completed")
        receipt = getattr(result, "receipt", None)
        receipt_id = str(getattr(receipt, "receipt_id", ""))
        if getattr(receipt, "outcome", "") != "committed" or not receipt_id:
            raise ParallelExecutionError("runtime_signed_receipt_required")
        store = getattr(runtime, "receipt_store", None)
        if store is None or not callable(getattr(store, "get", None)):
            raise ParallelExecutionError("runtime_receipt_store_required")
        stored = store.get(receipt_id)
        if stored is None or str(getattr(stored, "receipt_id", "")) != receipt_id or getattr(stored, "outcome", "") != "committed":
            raise ParallelExecutionError("runtime_receipt_not_verified")
        return {"request_id": str(getattr(result, "request_id", "")), "receipt_id": receipt_id, "outcome": "committed", "sandboxed": bool(getattr(result, "sandboxed", False))}

    def resume_delegated(
        self,
        session_id: str,
        requests: Sequence[TaskExecutionRequest],
        callback: Callable[[AgentLaneContext], object],
        *,
        approval_ids: Mapping[str, str],
        request_digests: Mapping[str, str],
        event_sink: Optional[Callable[[Mapping[str, object]], None]] = None,
        lease_store: object | None = None,
        cancellation: object | None = None,
        max_duration_seconds: float | None = None,
        retry_limit: int = 0,
    ) -> TaskExecutionReport:
        """Resume interrupted delegated tasks only after explicit single-use approvals."""
        if self.delegated_resume_store is None:
            raise TaskExecutionBridgeError("delegated_resume_store_required")
        if not requests:
            raise TaskExecutionBridgeError("execution_requests_required")
        for request in requests:
            approval_id = str(approval_ids.get(request.task_id, ""))
            request_digest = str(request_digests.get(request.task_id, ""))
            if not approval_id or not request_digest:
                raise TaskExecutionBridgeError("fresh_resume_approval_required")
            try:
                self.delegated_resume_store.consume_resume_approval(request.task_id, approval_id, request_digest=request_digest)
                task = self.tasks.task(request.task_id)
                if task.session_id != session_id:
                    raise TaskExecutionBridgeError("task_session_mismatch")
                if task.state == "failed":
                    self.tasks.transition_task(request.task_id, "planned", reason="approved_delegated_resume", command_id="delegated-resume-planned-" + request.task_id + "-" + approval_id)
                if self.tasks.task(request.task_id).state != "waiting_approval":
                    self.tasks.transition_task(request.task_id, "waiting_approval", reason="approved_delegated_resume", command_id="delegated-resume-approval-" + request.task_id + "-" + approval_id)
            except (DelegatedResumeError, TaskSessionError) as exc:
                if isinstance(exc, TaskExecutionBridgeError):
                    raise
                raise TaskExecutionBridgeError(str(exc)) from exc
            if event_sink is not None:
                event_sink({"kind": "delegation_resume_approved", "session_id": session_id, "task_id": request.task_id, "approval_id": approval_id, "execution_claim": "resume_authorized"})
        return self.execute(session_id, requests, callback, approval=True, event_sink=event_sink, lease_store=lease_store, cancellation=cancellation, max_duration_seconds=max_duration_seconds, retry_limit=retry_limit)

    def execute_runtime(
        self,
        session_id: str,
        requests: Sequence[TaskExecutionRequest],
        runtime_factory: Callable[[AgentLaneContext], tuple[Any, Any]],
        *,
        approval: bool = False,
        event_sink: Optional[Callable[[Mapping[str, object]], None]] = None,
        lease_store: object | None = None,
        cancellation: object | None = None,
        max_duration_seconds: float | None = None,
        retry_limit: int = 0,
    ) -> TaskExecutionReport:
        """Run approved lanes through an injected ChildExecutionRuntime and expose only receipt metadata."""
        if not callable(runtime_factory):
            raise TaskExecutionBridgeError("runtime_factory_required")

        def callback(context: AgentLaneContext) -> Mapping[str, Any]:
            runtime, request = runtime_factory(context)
            request_workspace = Path(str(getattr(request, "workspace", ""))).expanduser().resolve()
            if request_workspace != context.workspace.resolve():
                raise ParallelExecutionError("runtime_workspace_mismatch")
            runner = getattr(runtime, "run", None)
            if not callable(runner):
                raise ParallelExecutionError("runtime_required")
            result = runner(request)
            evidence = self._runtime_evidence(runtime, result)
            if not evidence["request_id"]:
                raise ParallelExecutionError("runtime_request_identity_required")
            return {"execution": evidence}

        return self.execute(session_id, requests, callback, approval=approval, event_sink=event_sink, lease_store=lease_store, cancellation=cancellation, max_duration_seconds=max_duration_seconds, retry_limit=retry_limit)


__all__ = ["TaskExecutionBridge", "TaskExecutionBridgeError", "TaskExecutionReport", "TaskExecutionRequest"]

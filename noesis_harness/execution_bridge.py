"""Approval-gated bridge from durable task sessions to safe parallel lanes.

The bridge only coordinates injected callbacks. It never invokes a model,
shell command, tool, or executable skill. Those operations remain behind the
Trust Plane and ChildExecutionRuntime boundaries.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Optional, Sequence

from .coordination import Actions
from .parallel_agent import AgentLane, AgentLaneContext, AgentLaneResult, ParallelExecutionError, SafeParallelExecutor
from .task_session_api import TaskSessionError, TaskSessionStore


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

    def __init__(self, tasks: TaskSessionStore, actions: Actions, executor: SafeParallelExecutor):
        self.tasks = tasks
        self.actions = actions
        self.executor = executor

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
            )
        except ParallelExecutionError as exc:
            raise TaskExecutionBridgeError(str(exc)) from exc

        for result in results:
            try:
                task = self.tasks.task(result.task_id)
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


__all__ = ["TaskExecutionBridge", "TaskExecutionBridgeError", "TaskExecutionReport", "TaskExecutionRequest"]

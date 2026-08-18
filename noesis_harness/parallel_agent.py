"""Safe bounded orchestration for local multi-agent callbacks.

This module schedules already-approved Python callbacks; it does not execute
model-generated code, shell commands, tools, or skills. Tool/skill execution
must cross ChildExecutionRuntime separately. The coordinator provides
workspace separation, capability validation, bounded concurrency, provenance
identity, and fail-isolated result collection.
"""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from threading import Event, Lock, Timer
import time
from typing import Callable, Iterable, Mapping, Optional, Sequence
from uuid import uuid4


class ParallelExecutionError(ValueError):
    """Raised when a multi-agent plan violates the local safety contract."""


class CancellationToken:
    """Cooperative cancellation state shared with one lane callback."""

    def __init__(self):
        self._event = Event()
        self._reason = ""

    def cancel(self, reason: str = "cancelled") -> None:
        self._reason = reason or "cancelled"
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    @property
    def reason(self) -> str:
        return self._reason or "cancelled"

    def check(self) -> None:
        if self.cancelled:
            raise ParallelExecutionError("lane_cancelled:" + self.reason)


SAFE_CAPABILITIES = frozenset({
    "read",
    "workspace_write",
    "memory_read",
    "memory_write",
    "signal_send",
    "provenance",
})
ALWAYS_DENIED_CAPABILITIES = frozenset({
    "credentials",
    "secret_read",
    "cross_agent_read",
    "shared_workspace",
    "inline_code",
    "unbounded_process",
    "shell",
})
APPROVAL_REQUIRED_CAPABILITIES = frozenset({"workspace_write", "memory_write", "signal_send"})


@dataclass(frozen=True)
class AgentLane:
    """Immutable execution request for one agent/task/workspace lane."""

    agent_id: str
    task_id: str
    workspace: str
    capabilities: tuple[str, ...] = ("read", "provenance")
    approval_required: bool = False
    approval_granted: bool = False


@dataclass(frozen=True)
class AgentLaneContext:
    """Non-secret context made available to one injected callback."""

    session_id: str
    task_id: str
    agent_id: str
    workspace: Path
    capabilities: frozenset[str]
    cancellation: CancellationToken | None = None
    deadline: float | None = None
    network_allowed: bool = False
    credentials_available: bool = False

    def check_cancelled(self) -> None:
        if self.cancellation is None:
            return
        self.cancellation.check()
        if self.deadline is not None and time.monotonic() >= self.deadline:
            self.cancellation.cancel("deadline_exceeded")
            self.cancellation.check()

    def path(self, relative: str) -> Path:
        """Resolve a relative path and reject traversal/symlink escapes."""
        if not relative or Path(relative).is_absolute():
            raise ParallelExecutionError("workspace_relative_path_required")
        candidate = (self.workspace / relative).resolve()
        try:
            candidate.relative_to(self.workspace)
        except ValueError as exc:
            raise ParallelExecutionError("workspace_escape") from exc
        current = self.workspace
        for part in candidate.relative_to(self.workspace).parts:
            current = current / part
            if current.is_symlink():
                raise ParallelExecutionError("workspace_symlink_escape")
        return candidate


@dataclass(frozen=True)
class AgentLaneResult:
    session_id: str
    task_id: str
    agent_id: str
    workspace: str
    status: str
    output: object = None
    error: str = ""
    attempts: int = 1
    recovered: bool = False


class SafeParallelExecutor:
    """Run bounded, non-overlapping orchestration callbacks in parallel.

    The callback receives only an :class:`AgentLaneContext`. No credentials,
    network capability, shell execution, or shared workspace is exposed. This
    is not an OS sandbox: executable tools and skills must use the separate
    child execution boundary.
    """

    MAX_CONCURRENCY = 8

    def __init__(self, workspace_root: str, *, max_concurrency: int = 2):
        root = Path(workspace_root).expanduser().resolve()
        if root.exists() and root.is_symlink():
            raise ParallelExecutionError("workspace_root_symlink")
        root.mkdir(parents=True, exist_ok=True)
        if not root.is_dir():
            raise ParallelExecutionError("workspace_root_not_directory")
        self.workspace_root = root
        self.max_concurrency = max(1, min(int(max_concurrency), self.MAX_CONCURRENCY))
        self._audit_lock = Lock()
        self.audit: list[dict[str, object]] = []

    def _validate_lanes(self, lanes: Sequence[AgentLane], approval: bool) -> list[AgentLaneContext]:
        if not lanes:
            raise ParallelExecutionError("lanes_required")
        contexts: list[AgentLaneContext] = []
        agent_ids: set[str] = set()
        task_ids: set[str] = set()
        paths: set[Path] = set()
        for lane in lanes:
            if not lane.agent_id or not lane.task_id:
                raise ParallelExecutionError("agent_and_task_identity_required")
            if lane.agent_id in agent_ids or lane.task_id in task_ids:
                raise ParallelExecutionError("duplicate_agent_or_task_identity")
            agent_ids.add(lane.agent_id)
            task_ids.add(lane.task_id)
            caps = frozenset(lane.capabilities)
            denied = caps & ALWAYS_DENIED_CAPABILITIES
            unknown = caps - SAFE_CAPABILITIES - ALWAYS_DENIED_CAPABILITIES
            if denied:
                raise ParallelExecutionError("capability_denied:" + ",".join(sorted(denied)))
            if unknown:
                raise ParallelExecutionError("capability_unknown:" + ",".join(sorted(unknown)))
            if lane.approval_required and not (approval and lane.approval_granted):
                raise ParallelExecutionError("approval_required:" + lane.agent_id)
            if caps & APPROVAL_REQUIRED_CAPABILITIES and not (approval and lane.approval_granted):
                raise ParallelExecutionError("capability_approval_required:" + lane.agent_id)
            raw = Path(lane.workspace).expanduser()
            if raw.is_absolute():
                path = raw.resolve()
            else:
                path = (self.workspace_root / raw).resolve()
            try:
                path.relative_to(self.workspace_root)
            except ValueError as exc:
                raise ParallelExecutionError("workspace_outside_root") from exc
            if path == self.workspace_root or path in paths:
                raise ParallelExecutionError("workspace_not_unique")
            if path.exists() and path.is_symlink():
                raise ParallelExecutionError("workspace_symlink")
            path.mkdir(parents=True, exist_ok=True)
            if path.is_symlink():
                raise ParallelExecutionError("workspace_symlink")
            paths.add(path)
            contexts.append(AgentLaneContext(
                session_id="",
                task_id=lane.task_id,
                agent_id=lane.agent_id,
                workspace=path,
                capabilities=caps,
            ))
        return contexts

    def execute(
        self,
        lanes: Iterable[AgentLane],
        callback: Callable[[AgentLaneContext], object],
        *,
        session_id: str | None = None,
        approval: bool = False,
        lease_store: object | None = None,
        action_store: object | None = None,
        event_sink: Optional[Callable[[Mapping[str, object]], None]] = None,
        max_duration_seconds: float | None = None,
        cancellation: CancellationToken | None = None,
        retry_limit: int = 0,
    ) -> list[AgentLaneResult]:
        """Execute callbacks with bounded concurrency and isolated failures."""
        if not callable(callback):
            raise ParallelExecutionError("callback_required")
        lane_list = list(lanes)
        if lease_store is not None:
            if not callable(getattr(lease_store, "acquire", None)) or not callable(getattr(lease_store, "release", None)):
                raise ParallelExecutionError("lease_store_invalid")
        if action_store is not None:
            required = ("claim", "complete", "requeue")
            if any(not callable(getattr(action_store, name, None)) for name in required):
                raise ParallelExecutionError("action_store_invalid")
        if max_duration_seconds is not None and max_duration_seconds <= 0:
            raise ParallelExecutionError("max_duration_seconds_must_be_positive")
        if int(retry_limit) < 0 or int(retry_limit) > 3:
            raise ParallelExecutionError("retry_limit_out_of_range")
        retry_limit = int(retry_limit)
        sid = session_id or uuid4().hex
        token = cancellation or CancellationToken()
        deadline = time.monotonic() + max_duration_seconds if max_duration_seconds is not None else None
        contexts = self._validate_lanes(lane_list, approval)
        contexts = [AgentLaneContext(sid, c.task_id, c.agent_id, c.workspace, c.capabilities, token, deadline) for c in contexts]
        results: list[AgentLaneResult] = []

        def emit(kind: str, context: AgentLaneContext, error: str = "") -> None:
            event = {"kind": kind, "session_id": sid, "task_id": context.task_id, "agent_id": context.agent_id}
            if error:
                event["error"] = error
            with self._audit_lock:
                self.audit.append({"event": kind, **event})
            if event_sink is not None:
                try:
                    event_sink(event)
                except Exception:
                    with self._audit_lock:
                        self.audit.append({"event": "lane_event_sink_failed", "session_id": sid, "task_id": context.task_id, "agent_id": context.agent_id})

        def run_one(context: AgentLaneContext) -> AgentLaneResult:
            claimed = False
            action_claimed = False
            attempts = 0
            emit("lane_started", context)
            if lease_store is not None:
                claim = lease_store.acquire(context.task_id, context.agent_id)
                if not claim.get("ok"):
                    emit("lane_blocked", context, "lease_held")
                    return AgentLaneResult(sid, context.task_id, context.agent_id, str(context.workspace), "blocked", error="lease_held")
                claimed = True
            if action_store is not None:
                if not action_store.claim(context.task_id, context.agent_id):
                    if claimed:
                        lease_store.release(context.task_id, context.agent_id)
                    emit("lane_blocked", context, "action_not_claimed")
                    return AgentLaneResult(sid, context.task_id, context.agent_id, str(context.workspace), "blocked", error="action_not_claimed")
                action_claimed = True
                emit("lane_claimed", context)
            try:
                while True:
                    attempts += 1
                    if retry_limit > 0:
                        emit("lane_attempt", context, "attempt_%d" % attempts)
                    try:
                        context.check_cancelled()
                        output = callback(context)
                        context.check_cancelled()
                        if action_claimed:
                            completion = action_store.complete(context.task_id)
                            if completion is False:
                                raise ParallelExecutionError("action_completion_rejected")
                            action_claimed = False
                        emit("lane_completed", context)
                        return AgentLaneResult(sid, context.task_id, context.agent_id, str(context.workspace), "passed", output=output, attempts=attempts, recovered=attempts > 1)
                    except Exception as exc:  # fail one lane without cancelling unrelated lanes
                        if isinstance(exc, ParallelExecutionError) and str(exc).startswith("lane_cancelled:"):
                            emit("lane_cancelled", context, str(exc))
                            if action_claimed:
                                action_store.requeue(context.task_id, context.agent_id)
                                action_claimed = False
                            return AgentLaneResult(sid, context.task_id, context.agent_id, str(context.workspace), "cancelled", error=str(exc), attempts=attempts)
                        if attempts <= retry_limit:
                            emit("lane_retry_scheduled", context, type(exc).__name__)
                            if action_claimed and action_store is not None:
                                action_store.requeue(context.task_id, context.agent_id)
                                action_claimed = action_store.claim(context.task_id, context.agent_id)
                                if not action_claimed:
                                    emit("lane_failed", context, "retry_reclaim_failed")
                                    return AgentLaneResult(sid, context.task_id, context.agent_id, str(context.workspace), "failed", error="retry_reclaim_failed", attempts=attempts)
                            continue
                        emit("lane_failed", context, type(exc).__name__)
                        if action_claimed:
                            action_store.requeue(context.task_id, context.agent_id)
                            action_claimed = False
                        return AgentLaneResult(sid, context.task_id, context.agent_id, str(context.workspace), "failed", error=type(exc).__name__ + ": " + str(exc), attempts=attempts)
            finally:
                if claimed:
                    lease_store.release(context.task_id, context.agent_id)

        with ThreadPoolExecutor(max_workers=self.max_concurrency, thread_name_prefix="noesis-agent") as pool:
            futures: dict[Future[AgentLaneResult], AgentLaneContext] = {pool.submit(run_one, context): context for context in contexts}
            for future in as_completed(futures):
                results.append(future.result())
        return sorted(results, key=lambda result: result.task_id)


__all__ = [
    "AgentLane",
    "CancellationToken",
    "AgentLaneContext",
    "AgentLaneResult",
    "ALWAYS_DENIED_CAPABILITIES",
    "ParallelExecutionError",
    "SAFE_CAPABILITIES",
    "SafeParallelExecutor",
]

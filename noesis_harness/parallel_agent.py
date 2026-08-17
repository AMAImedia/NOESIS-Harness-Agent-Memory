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
from threading import Lock
from typing import Callable, Iterable, Mapping, Sequence
from uuid import uuid4


class ParallelExecutionError(ValueError):
    """Raised when a multi-agent plan violates the local safety contract."""


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
    network_allowed: bool = False
    credentials_available: bool = False

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
    ) -> list[AgentLaneResult]:
        """Execute callbacks with bounded concurrency and isolated failures."""
        if not callable(callback):
            raise ParallelExecutionError("callback_required")
        lane_list = list(lanes)
        if lease_store is not None:
            if not callable(getattr(lease_store, "acquire", None)) or not callable(getattr(lease_store, "release", None)):
                raise ParallelExecutionError("lease_store_invalid")
        sid = session_id or uuid4().hex
        contexts = self._validate_lanes(lane_list, approval)
        contexts = [AgentLaneContext(sid, c.task_id, c.agent_id, c.workspace, c.capabilities) for c in contexts]
        results: list[AgentLaneResult] = []

        def run_one(context: AgentLaneContext) -> AgentLaneResult:
            claimed = False
            with self._audit_lock:
                self.audit.append({"event": "lane_started", "session_id": sid, "task_id": context.task_id, "agent_id": context.agent_id})
            if lease_store is not None:
                claim = lease_store.acquire(context.task_id, context.agent_id)
                if not claim.get("ok"):
                    with self._audit_lock:
                        self.audit.append({"event": "lane_blocked", "session_id": sid, "task_id": context.task_id, "agent_id": context.agent_id})
                    return AgentLaneResult(sid, context.task_id, context.agent_id, str(context.workspace), "blocked", error="lease_held")
                claimed = True
            try:
                output = callback(context)
            except Exception as exc:  # fail one lane without cancelling unrelated lanes
                with self._audit_lock:
                    self.audit.append({"event": "lane_failed", "session_id": sid, "task_id": context.task_id, "agent_id": context.agent_id})
                return AgentLaneResult(sid, context.task_id, context.agent_id, str(context.workspace), "failed", error=type(exc).__name__ + ": " + str(exc))
            finally:
                if claimed:
                    lease_store.release(context.task_id, context.agent_id)
            with self._audit_lock:
                self.audit.append({"event": "lane_completed", "session_id": sid, "task_id": context.task_id, "agent_id": context.agent_id})
            return AgentLaneResult(sid, context.task_id, context.agent_id, str(context.workspace), "passed", output=output)

        with ThreadPoolExecutor(max_workers=self.max_concurrency, thread_name_prefix="noesis-agent") as pool:
            futures: dict[Future[AgentLaneResult], AgentLaneContext] = {pool.submit(run_one, context): context for context in contexts}
            for future in as_completed(futures):
                results.append(future.result())
        return sorted(results, key=lambda result: result.task_id)


__all__ = [
    "AgentLane",
    "AgentLaneContext",
    "AgentLaneResult",
    "ALWAYS_DENIED_CAPABILITIES",
    "ParallelExecutionError",
    "SAFE_CAPABILITIES",
    "SafeParallelExecutor",
]

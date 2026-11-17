"""Durable coordination layer for isolated multi-agent sessions."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from .event_store import EventStore
from .task_session_api import TaskSessionError, TaskSessionStore
from .workspaces import WorkspaceManager

MULTI_AGENT_SCHEMA = "noesis.multi-agent.v1"


class MultiAgentError(ValueError):
    """Raised for invalid agent coordination commands."""


@dataclass(frozen=True)
class AgentDescriptor:
    agent_id: str
    role: str
    capabilities: tuple[str, ...]
    workspace_id: Optional[str] = None


@dataclass(frozen=True)
class Claim:
    task_id: str
    agent_id: str
    workspace_id: str
    claimed_at: float


class MultiAgentCoordinator:
    """Coordinate exclusive task claims without mixing agent workspaces."""

    def __init__(self, task_store: TaskSessionStore, workspace_manager: WorkspaceManager, event_path: str):
        self.tasks = task_store
        self.workspaces = workspace_manager
        self.events = EventStore(event_path)
        self._agents: dict[str, AgentDescriptor] = {}
        self._claims: dict[str, Claim] = {}
        self._lock = threading.RLock()

    def register_agent(self, agent_id: str, role: str, capabilities: tuple[str, ...] = ()) -> AgentDescriptor:
        if not agent_id or not role or agent_id in self._agents:
            raise MultiAgentError("invalid_or_duplicate_agent")
        descriptor = AgentDescriptor(agent_id, role, tuple(sorted(set(capabilities))))
        self._agents[agent_id] = descriptor
        self.events.append("agent_registered", {"schema_version": MULTI_AGENT_SCHEMA, "agent_id": agent_id, "role": role, "capabilities": list(descriptor.capabilities)})
        return descriptor

    def claim(self, session_id: str, task_id: str, agent_id: str) -> Claim:
        with self._lock:
            if agent_id not in self._agents:
                raise MultiAgentError("agent_not_registered")
            if task_id in self._claims:
                raise MultiAgentError("task_already_claimed")
            task = self.tasks.task(task_id)
            if task.session_id != session_id:
                raise MultiAgentError("task_session_mismatch")
            if task.state == "created":
                self.tasks.transition_task(task_id, "planned", reason="coordinator_planned")
                task = self.tasks.task(task_id)
            if task.state not in {"planned", "failed", "rolled_back"}:
                raise MultiAgentError("task_not_claimable:%s" % task.state)
            if task.state in {"failed", "rolled_back"}:
                self.tasks.transition_task(task_id, "planned", reason="coordinator_retry")
            self.tasks.transition_task(task_id, "executing", reason="claimed_by:%s" % agent_id)
            workspace_id = self.workspaces.create(session_id, agent_id)
            claim = Claim(task_id, agent_id, workspace_id, time.time())
            self._claims[task_id] = claim
            self.events.append("task_claimed", {"schema_version": MULTI_AGENT_SCHEMA, "session_id": session_id, "task_id": task_id, "agent_id": agent_id, "workspace_id": workspace_id, "claimed_at": claim.claimed_at})
            return claim

    def complete_for_review(self, task_id: str, agent_id: str, summary: str = "") -> Mapping[str, Any]:
        with self._lock:
            claim = self._claims.get(task_id)
            if not claim or claim.agent_id != agent_id:
                raise MultiAgentError("claim_owner_required")
            task = self.tasks.task(task_id)
            if task.state != "executing":
                raise MultiAgentError("task_not_executing")
            self.tasks.transition_task(task_id, "review", reason="agent_completed:%s" % agent_id)
            payload = {"schema_version": MULTI_AGENT_SCHEMA, "task_id": task_id, "agent_id": agent_id, "workspace_id": claim.workspace_id, "summary": summary[:4096], "status": "review"}
            self.events.append("task_review_ready", payload)
            return payload

    def handoff(self, task_id: str, from_agent: str, to_agent: str, note: str = "") -> Mapping[str, Any]:
        with self._lock:
            claim = self._claims.get(task_id)
            if not claim or claim.agent_id != from_agent:
                raise MultiAgentError("handoff_owner_required")
            if to_agent not in self._agents:
                raise MultiAgentError("target_agent_not_registered")
            payload = {"schema_version": MULTI_AGENT_SCHEMA, "task_id": task_id, "from_agent": from_agent, "to_agent": to_agent, "workspace_id": claim.workspace_id, "note": note[:4096], "created_at": time.time()}
            self.events.append("task_handoff", payload)
            self._claims[task_id] = Claim(task_id, to_agent, claim.workspace_id, claim.claimed_at)
            return payload

    def resume(self, session_id: str) -> Mapping[str, Any]:
        tasks = []
        for task_id in tuple(self.tasks._project()["tasks"]):
            task = self.tasks.task(task_id)
            if task.session_id == session_id:
                tasks.append(task)
        claims = tuple(claim for claim in self._claims.values() if any(task.task_id == claim.task_id for task in tasks))
        return {"schema_version": MULTI_AGENT_SCHEMA, "session_id": session_id, "agents": tuple(self._agents.values()), "tasks": tuple(tasks), "claims": claims, "event_count": self.events.count()}


__all__ = ["MULTI_AGENT_SCHEMA", "AgentDescriptor", "Claim", "MultiAgentCoordinator", "MultiAgentError"]

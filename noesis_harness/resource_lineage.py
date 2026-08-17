"""Observation lineage and taint-aware egress policy for agent workspaces."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Tuple

from .event_store import EventStore

LINEAGE_SCHEMA = "noesis.resource-lineage.v1"
SENSITIVITIES = frozenset({"public", "internal", "sensitive", "restricted"})


class LineageError(ValueError):
    """Raised when an observation or egress request is invalid."""


@dataclass(frozen=True)
class Observation:
    session_id: str
    agent_id: str
    resource_id: str
    source: str
    sensitivity: str = "internal"
    content_digest: str = ""
    parent_observation: Optional[str] = None


@dataclass(frozen=True)
class EgressDecision:
    allowed: bool
    reason: str
    observed_resources: Tuple[str, ...]
    blocked_sensitivities: Tuple[str, ...]


class ObservationLedger:
    """Record what an agent has seen and enforce taint-aware egress decisions."""

    def __init__(self, event_path: str):
        self.events = EventStore(event_path)

    @staticmethod
    def digest_content(content: Any) -> str:
        if isinstance(content, bytes):
            data = content
        else:
            data = json.dumps(content, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
        return "sha256:" + hashlib.sha256(data).hexdigest()

    def record(self, observation: Observation) -> str:
        if not observation.session_id or not observation.agent_id or not observation.resource_id or not observation.source:
            raise LineageError("observation identity is required")
        if observation.sensitivity not in SENSITIVITIES:
            raise LineageError("invalid_sensitivity")
        digest = observation.content_digest or self.digest_content(observation.resource_id)
        payload = {"schema_version": LINEAGE_SCHEMA, "session_id": observation.session_id, "agent_id": observation.agent_id, "resource_id": observation.resource_id, "source": observation.source, "sensitivity": observation.sensitivity, "content_digest": digest, "parent_observation": observation.parent_observation, "observed_at": time.time()}
        identity = {key: payload[key] for key in ("session_id", "agent_id", "resource_id", "source", "sensitivity", "content_digest", "parent_observation")}
        event_id = "observation:" + hashlib.sha256(json.dumps(identity, sort_keys=True).encode("utf-8")).hexdigest()
        return self.events.append("resource_observed", payload, event_id=event_id)

    def observations(self, session_id: str, agent_id: Optional[str] = None) -> Tuple[Mapping[str, Any], ...]:
        rows = []
        for event in self.events.iter_events() or ():
            if event.get("type") != "resource_observed":
                continue
            payload = event.get("payload") or {}
            if payload.get("session_id") != session_id:
                continue
            if agent_id is not None and payload.get("agent_id") != agent_id:
                continue
            rows.append(payload)
        return tuple(rows)

    def decide_egress(self, session_id: str, agent_id: str, target: str, *, allowed_sensitivities: Tuple[str, ...] = ("public", "internal"), explicit_approval: bool = False) -> EgressDecision:
        if not target:
            raise LineageError("egress target is required")
        allowed = set(allowed_sensitivities)
        if not allowed.issubset(SENSITIVITIES):
            raise LineageError("unknown_allowed_sensitivity")
        observed = self.observations(session_id, agent_id)
        blocked = tuple(sorted({str(item.get("sensitivity")) for item in observed if item.get("sensitivity") not in allowed}))
        resources = tuple(str(item.get("resource_id")) for item in observed)
        if blocked and not explicit_approval:
            return EgressDecision(False, "tainted_by_observed_resource", resources, blocked)
        if blocked and target.startswith("external:") and not explicit_approval:
            return EgressDecision(False, "external_egress_requires_approval", resources, blocked)
        return EgressDecision(True, "explicit_approval" if blocked else "policy_allows", resources, blocked)


__all__ = ["EgressDecision", "LINEAGE_SCHEMA", "LineageError", "Observation", "ObservationLedger", "SENSITIVITIES"]

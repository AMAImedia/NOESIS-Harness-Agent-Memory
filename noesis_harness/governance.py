"""NOESIS governance and orchestration primitives, stdlib-only.

These APIs are deliberately conservative: risky actions are staged or simulated,
not executed; Markdown is a projection, not an implicit authority; and a missing
hardened sandbox is reported as unavailable rather than disguised as safe.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from .nextgen import AuditChain, CapabilityDenied, CapabilityManifest
except ImportError:
    from noesis_nextgen import AuditChain, CapabilityDenied, CapabilityManifest


_EFFECTS = {"read", "write", "network_read", "network_write", "secret_use", "irreversible"}
_RISKY = {"write", "network_write", "secret_use", "irreversible"}
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


@dataclass(frozen=True)
class ActionRequest:
    actor: str
    operation: str
    target: str
    effect: str = "read"
    payload_digest: str = ""
    request_id: str = ""

    def __post_init__(self):
        if self.effect not in _EFFECTS:
            raise ValueError("unknown side-effect class")


class Gatekeeper:
    """Capability and side-effect gate; no side effect is performed here."""

    def __init__(self, audit: Optional[AuditChain] = None):
        self.audit = audit

    def decide(self, request: ActionRequest, manifest: CapabilityManifest, approved: bool = False, simulation: Any = None) -> Dict[str, Any]:
        rid = request.request_id or uuid.uuid4().hex
        allowed = manifest.allows(request.operation, request.target)
        if not allowed:
            result = {"request_id": rid, "status": "denied", "reason": "capability_denied", "simulated": False}
        elif request.effect in _RISKY and not approved:
            result = {"request_id": rid, "status": "pending", "reason": "approval_required", "simulated": True, "simulation": simulation}
        else:
            result = {"request_id": rid, "status": "approved", "reason": "policy_allowed", "simulated": False}
        if self.audit:
            self.audit.append(request.actor, "gatekeeper_decision", {**result, "operation": request.operation, "target": request.target, "effect": request.effect})
        return result


@dataclass(frozen=True)
class TaskNode:
    task_id: str
    deps: Tuple[str, ...] = ()
    role: str = "worker"
    budget: int = 1


class DAGPlanner:
    """Deterministic dependency planner with cycle and budget checks."""

    def __init__(self, max_parallel: int = 4):
        if max_parallel < 1:
            raise ValueError("max_parallel must be positive")
        self.max_parallel = max_parallel
        self._nodes: Dict[str, TaskNode] = {}

    def add(self, task_id: str, deps: Sequence[str] = (), role: str = "worker", budget: int = 1) -> None:
        if not task_id or task_id in self._nodes or budget < 1:
            raise ValueError("invalid or duplicate task")
        self._nodes[task_id] = TaskNode(task_id, tuple(deps), role, budget)

    def stages(self) -> List[Tuple[str, ...]]:
        unknown = sorted({d for n in self._nodes.values() for d in n.deps if d not in self._nodes})
        if unknown:
            raise ValueError("unknown dependency: " + unknown[0])
        remaining = set(self._nodes)
        done: set[str] = set()
        result: List[Tuple[str, ...]] = []
        while remaining:
            ready = sorted(t for t in remaining if set(self._nodes[t].deps) <= done)
            if not ready:
                raise ValueError("dependency cycle detected")
            while ready:
                batch = tuple(ready[: self.max_parallel])
                result.append(batch)
                done.update(batch)
                remaining.difference_update(batch)
                ready = sorted(t for t in remaining if set(self._nodes[t].deps) <= done)
        return result


@dataclass(frozen=True)
class VaultNote:
    note_id: str
    title: str
    body: str
    tags: Tuple[str, ...] = ()
    source_ids: Tuple[str, ...] = ()
    updated_at: float = field(default_factory=time.time)


class VaultProjector:
    """Safe Markdown/Obsidian projection with stable IDs and atomic writes."""

    def __init__(self, root: str):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, note_id: str) -> Path:
        if not _SAFE_ID.fullmatch(note_id):
            raise ValueError("invalid note id")
        path = (self.root / (note_id + ".md")).resolve()
        try:
            path.relative_to(self.root)
        except ValueError:
            raise ValueError("note escapes vault")
        return path

    def write(self, note: VaultNote) -> Path:
        path = self._path(note.note_id)
        tags = ", ".join(note.tags)
        sources = ", ".join(note.source_ids)
        text = ("---\n" f"id: {note.note_id}\n" f"title: {note.title}\n" f"updated_at: {note.updated_at:.6f}\n" f"tags: [{tags}]\n" f"sources: [{sources}]\n" "---\n\n" + note.body.rstrip() + "\n")
        fd, tmp = tempfile.mkstemp(prefix=".noesis-", suffix=".tmp", dir=str(self.root), text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        return path

    def read(self, note_id: str) -> VaultNote:
        path = self._path(note_id)
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            raise ValueError("missing frontmatter")
        _, front, body = text.split("---\n", 2)
        fields: Dict[str, str] = {}
        for line in front.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                fields[key.strip()] = value.strip()
        def list_field(name: str) -> Tuple[str, ...]:
            raw = fields.get(name, "[]").strip().strip("[]")
            return tuple(x.strip() for x in raw.split(",") if x.strip())
        return VaultNote(fields.get("id", note_id), fields.get("title", note_id), body.lstrip(), list_field("tags"), list_field("sources"), float(fields.get("updated_at", "0")))

    def list_ids(self) -> List[str]:
        return sorted(p.stem for p in self.root.glob("*.md") if _SAFE_ID.fullmatch(p.stem))


@dataclass(frozen=True)
class SkillProposal:
    proposal_id: str
    name: str
    content: str
    digest: str
    created_at: float
    status: str = "pending"


class SkillGate:
    """Stages self-authored skills; approval requires caller-supplied tests."""

    def __init__(self, root: str):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._pending: Dict[str, SkillProposal] = {}

    def stage(self, name: str, content: str) -> SkillProposal:
        if not _SAFE_ID.fullmatch(name) or not content.strip():
            raise ValueError("invalid skill")
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        proposal = SkillProposal(uuid.uuid4().hex, name, content, digest, time.time())
        self._pending[proposal.proposal_id] = proposal
        return proposal

    def pending(self) -> List[SkillProposal]:
        return list(self._pending.values())

    def decide(self, proposal_id: str, approve: bool, tests: Optional[Callable[[], bool]] = None) -> SkillProposal:
        proposal = self._pending.get(proposal_id)
        if proposal is None:
            raise KeyError(proposal_id)
        if not approve:
            result = SkillProposal(proposal.proposal_id, proposal.name, proposal.content, proposal.digest, proposal.created_at, "rejected")
            del self._pending[proposal_id]
            return result
        if tests is None or not tests():
            raise PermissionError("approved skill requires passing tests")
        skill_dir = self.root / proposal.name
        skill_dir.mkdir(parents=True, exist_ok=False)
        (skill_dir / "SKILL.md").write_text(proposal.content, encoding="utf-8")
        result = SkillProposal(proposal.proposal_id, proposal.name, proposal.content, proposal.digest, proposal.created_at, "approved")
        del self._pending[proposal_id]
        return result


class ExecutionLadder:
    """Capability ladder; reports unavailable instead of faking a sandbox."""

    TIERS = ("workspace", "simulated_code", "subprocess", "browser", "sandbox")

    def __init__(self, available: Optional[Iterable[str]] = None):
        self.available = set(available or ("workspace", "simulated_code"))

    def choose(self, required: str) -> Dict[str, Any]:
        if required not in self.TIERS:
            raise ValueError("unknown execution tier")
        idx = self.TIERS.index(required)
        missing = [x for x in self.TIERS[: idx + 1] if x not in self.available]
        if missing:
            return {"status": "unavailable", "required": required, "missing": missing, "safe": True}
        return {"status": "available", "tier": required, "safe": required != "subprocess" or "sandbox" in self.available}


__all__ = ["ActionRequest", "Gatekeeper", "TaskNode", "DAGPlanner", "VaultNote", "VaultProjector", "SkillProposal", "SkillGate", "ExecutionLadder"]

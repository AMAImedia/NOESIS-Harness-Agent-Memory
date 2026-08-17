"""Per-agent workspace and review-only patch primitives.

Workspaces are isolated directories with deterministic SHA-256 manifests. The
module can propose and review diffs, but does not merge or publish changes.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

WORKSPACE_SCHEMA = "noesis.workspace.v1"
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class WorkspaceError(ValueError):
    """Raised for workspace policy violations."""


@dataclass(frozen=True)
class FileEntry:
    path: str
    sha256: str
    size: int

    def as_dict(self) -> dict[str, Any]:
        return {"path": self.path, "sha256": self.sha256, "size": self.size}


@dataclass(frozen=True)
class WorkspaceSnapshot:
    snapshot_id: str
    workspace_id: str
    parent_snapshot_id: Optional[str]
    created_at: float
    files: tuple[FileEntry, ...]

    def as_dict(self) -> dict[str, Any]:
        return {"schema_version": WORKSPACE_SCHEMA, "snapshot_id": self.snapshot_id, "workspace_id": self.workspace_id, "parent_snapshot_id": self.parent_snapshot_id, "created_at": self.created_at, "files": [entry.as_dict() for entry in self.files]}


@dataclass(frozen=True)
class PatchProposal:
    proposal_id: str
    workspace_id: str
    base_snapshot_id: str
    head_snapshot_id: str
    changes: tuple[Mapping[str, Any], ...]
    status: str = "needs_review"


class WorkspaceManager:
    """Manage agent workspaces under one explicit root."""

    def __init__(self, root: str):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._snapshots: dict[str, WorkspaceSnapshot] = {}

    @staticmethod
    def _validate_id(value: str, label: str) -> str:
        if not value or not _SAFE_ID.fullmatch(value):
            raise WorkspaceError("invalid_%s" % label)
        return value

    def create(self, session_id: str, agent_id: str) -> str:
        self._validate_id(session_id, "session_id")
        self._validate_id(agent_id, "agent_id")
        workspace_id = "%s--%s--%s" % (session_id, agent_id, uuid.uuid4().hex[:12])
        path = self.root / workspace_id
        path.mkdir(parents=True, exist_ok=False)
        (path / ".noesis-workspace").write_text(json.dumps({"schema_version": WORKSPACE_SCHEMA, "workspace_id": workspace_id, "session_id": session_id, "agent_id": agent_id}, sort_keys=True), encoding="utf-8")
        return workspace_id

    def path(self, workspace_id: str) -> Path:
        self._validate_id(workspace_id, "workspace_id")
        path = (self.root / workspace_id).resolve()
        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise WorkspaceError("workspace_outside_root") from exc
        if not path.is_dir():
            raise WorkspaceError("workspace_missing")
        return path

    def safe_file(self, workspace_id: str, relative_path: str) -> Path:
        if not relative_path or relative_path.startswith(("/", "\\")):
            raise WorkspaceError("absolute_path_forbidden")
        workspace = self.path(workspace_id)
        candidate = (workspace / relative_path).resolve()
        try:
            candidate.relative_to(workspace)
        except ValueError as exc:
            raise WorkspaceError("path_escape") from exc
        if candidate.name == ".noesis-workspace":
            raise WorkspaceError("workspace_marker_is_immutable")
        return candidate

    def write_text(self, workspace_id: str, relative_path: str, content: str) -> Path:
        if not isinstance(content, str):
            raise WorkspaceError("text_content_required")
        target = self.safe_file(workspace_id, relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    @staticmethod
    def _manifest(path: Path) -> tuple[FileEntry, ...]:
        entries = []
        for item in sorted(path.rglob("*")):
            if not item.is_file() or item.name == ".noesis-workspace":
                continue
            digest = hashlib.sha256(item.read_bytes()).hexdigest()
            entries.append(FileEntry(item.relative_to(path).as_posix(), digest, item.stat().st_size))
        return tuple(entries)

    def snapshot(self, workspace_id: str, parent_snapshot_id: Optional[str] = None) -> WorkspaceSnapshot:
        self.path(workspace_id)
        snapshot = WorkspaceSnapshot("snap_" + uuid.uuid4().hex, workspace_id, parent_snapshot_id, time.time(), self._manifest(self.path(workspace_id)))
        self._snapshots[snapshot.snapshot_id] = snapshot
        return snapshot

    def get_snapshot(self, snapshot_id: str) -> WorkspaceSnapshot:
        try:
            return self._snapshots[snapshot_id]
        except KeyError as exc:
            raise WorkspaceError("snapshot_not_found") from exc

    def propose_patch(self, base_snapshot_id: str, head_snapshot_id: str) -> PatchProposal:
        base = self.get_snapshot(base_snapshot_id)
        head = self.get_snapshot(head_snapshot_id)
        if base.workspace_id != head.workspace_id:
            raise WorkspaceError("snapshot_workspace_mismatch")
        before = {entry.path: entry for entry in base.files}
        after = {entry.path: entry for entry in head.files}
        changes = []
        for path in sorted(set(before) | set(after)):
            if path not in before:
                changes.append({"path": path, "kind": "added", "after": after[path].as_dict()})
            elif path not in after:
                changes.append({"path": path, "kind": "deleted", "before": before[path].as_dict()})
            elif before[path] != after[path]:
                changes.append({"path": path, "kind": "modified", "before": before[path].as_dict(), "after": after[path].as_dict()})
        return PatchProposal("patch_" + uuid.uuid4().hex, base.workspace_id, base.snapshot_id, head.snapshot_id, tuple(changes))

    @staticmethod
    def review(proposal: PatchProposal, decision: str) -> PatchProposal:
        if decision not in {"approved", "rejected"}:
            raise WorkspaceError("invalid_patch_review")
        return PatchProposal(proposal.proposal_id, proposal.workspace_id, proposal.base_snapshot_id, proposal.head_snapshot_id, proposal.changes, decision)


__all__ = ["WORKSPACE_SCHEMA", "FileEntry", "WorkspaceSnapshot", "PatchProposal", "WorkspaceManager", "WorkspaceError"]

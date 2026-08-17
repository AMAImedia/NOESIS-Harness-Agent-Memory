"""Transactional install and rollback store for verified NOESIS skills.

Patterns are borrowed from append-only event logs, atomic deployment pointers,
content-addressed package stores, and NOESIS best-state/recovery protection.
The store never imports or executes skill code and never deletes an installed
version; failed operations leave the active verified version unchanged.
"""

import hashlib
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Mapping, Optional

from .skill_import import ImportAssessment
from .skill_manifest import MANIFEST_FILENAME, SkillManifest, SkillManifestError


class SkillStoreError(ValueError):
    """Raised when a transactional skill operation is invalid."""


def _safe_component(value: str) -> str:
    if not value or value in {".", ".."} or any(char in value for char in "/\\"):
        raise SkillStoreError("unsafe skill path component")
    return value


class SkillStore:
    """Keep immutable verified versions and an atomic active-version pointer."""

    def __init__(self, root: str):
        self.root = Path(root).expanduser().resolve()
        self.skills_root = self.root / "skills"
        self.audit_path = self.root / "audit.jsonl"
        self.skills_root.mkdir(parents=True, exist_ok=True)

    def _audit(self, event: Mapping[str, Any]) -> None:
        payload = dict(event)
        payload["timestamp"] = time.time()
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        payload["event_id"] = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

    def _skill_dir(self, skill_id: str) -> Path:
        return self.skills_root / _safe_component(skill_id)

    def _active_path(self, skill_id: str) -> Path:
        return self._skill_dir(skill_id) / "active.json"

    def _read_active(self, skill_id: str) -> Optional[Mapping[str, Any]]:
        path = self._active_path(skill_id)
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SkillStoreError("active pointer unreadable: %s" % exc)
        return data if isinstance(data, Mapping) else None

    def _atomic_write(self, path: Path, data: Mapping[str, Any]) -> None:
        temporary = path.with_name(path.name + ".next")
        temporary.write_text(json.dumps(dict(data), sort_keys=True) + "\n", encoding="utf-8")
        os.replace(str(temporary), str(path))

    def install_approved(self, assessment: ImportAssessment) -> Mapping[str, Any]:
        if assessment.status != "approved" or not assessment.staging_path:
            self._audit({"type": "skill_install", "skill_id": "unknown", "version": None, "previous": None, "status": "rolled_back", "reason": "approval_required:%s" % assessment.reason})
            raise SkillStoreError("approved assessment required")
        staged = Path(assessment.staging_path).resolve()
        marker = staged / ".approved"
        if not marker.is_file():
            raise SkillStoreError("approval marker missing")
        try:
            manifest = SkillManifest.from_file(str(staged / MANIFEST_FILENAME))
        except (OSError, SkillManifestError) as exc:
            raise SkillStoreError("approved manifest invalid: %s" % exc)
        skill_dir = self._skill_dir(manifest.skill_id)
        versions = skill_dir / "versions"
        versions.mkdir(parents=True, exist_ok=True)
        target = versions / _safe_component(manifest.version)
        if target.exists():
            raise SkillStoreError("version already installed")
        previous = self._read_active(manifest.skill_id)
        temporary = versions / ("." + manifest.version + ".pending")
        try:
            temporary.mkdir(parents=True, exist_ok=False)
            for source in sorted(staged.rglob("*")):
                relative = source.relative_to(staged)
                if relative.parts and relative.parts[0] == ".approved":
                    continue
                destination = temporary / relative
                if source.is_symlink():
                    raise SkillStoreError("symlink_detected")
                if source.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                elif source.is_file():
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(str(source), str(destination))
            os.replace(str(temporary), str(target))
            current = {"skill_id": manifest.skill_id, "version": manifest.version, "digest": manifest.digest}
            self._atomic_write(self._active_path(manifest.skill_id), current)
            self._audit({"type": "skill_install", "skill_id": manifest.skill_id, "version": manifest.version, "previous": previous, "status": "committed"})
            return current
        except (OSError, SkillStoreError) as exc:
            self._audit({"type": "skill_install", "skill_id": manifest.skill_id, "version": manifest.version, "previous": previous, "status": "rolled_back", "reason": str(exc)})
            raise

    def active(self, skill_id: str) -> Optional[Mapping[str, Any]]:
        return self._read_active(skill_id)

    def rollback(self, skill_id: str) -> Mapping[str, Any]:
        current = self._read_active(skill_id)
        if not current:
            raise SkillStoreError("no active skill to rollback")
        versions = self._skill_dir(skill_id) / "versions"
        candidates = []
        for path in versions.iterdir() if versions.is_dir() else ():
            if path.is_dir() and path.name != str(current.get("version")) and not path.name.startswith("."):
                manifest_path = path / MANIFEST_FILENAME
                if manifest_path.is_file():
                    try:
                        manifest = SkillManifest.from_file(str(manifest_path))
                        candidates.append((manifest.version, manifest.digest))
                    except (OSError, SkillManifestError):
                        continue
        if not candidates:
            raise SkillStoreError("no previous verified version")
        candidates.sort()
        version, digest = candidates[-1]
        previous = {"skill_id": skill_id, "version": version, "digest": digest}
        self._atomic_write(self._active_path(skill_id), previous)
        self._audit({"type": "skill_rollback", "skill_id": skill_id, "from": current, "to": previous, "status": "committed"})
        return previous

    def audit_events(self):
        if not self.audit_path.is_file():
            return ()
        return tuple(json.loads(line) for line in self.audit_path.read_text(encoding="utf-8").splitlines() if line.strip())


__all__ = ["SkillStore", "SkillStoreError"]

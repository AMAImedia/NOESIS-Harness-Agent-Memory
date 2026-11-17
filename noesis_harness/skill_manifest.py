"""Strict `.noesisskill` manifest format for portable NOESIS skills.

Patterns are borrowed from signed package manifests, content-addressed
artifacts, and NOESIS safe-import gates. This module parses metadata only; it
never imports skill code, follows links, executes entrypoints, or trusts a
manifest to grant capabilities.
"""

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, Tuple

MANIFEST_FORMAT_VERSION = "1.0"
MANIFEST_FILENAME = ".noesisskill"
ALLOWED_CAPABILITIES = frozenset({"health.read", "models.read", "chat", "tools.invoke", "skill.execute", "memory.read", "memory.write"})
ALLOWED_PLATFORMS = frozenset({"windows", "macos", "linux", "any"})
_FORBIDDEN_KEYS = frozenset({"token", "secret", "password", "credential", "authorization", "api_key", "private_key"})


class SkillManifestError(ValueError):
    """Raised when a skill manifest is invalid or unsafe."""


def _reject_secret_keys(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = str(key).lower().replace("-", "_").replace(" ", "_")
            if normalized in _FORBIDDEN_KEYS or any(part in normalized for part in ("token", "secret", "password", "credential", "authorization")):
                raise SkillManifestError("secret-shaped manifest key is forbidden: %s" % key)
            _reject_secret_keys(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _reject_secret_keys(nested)


def _validate_relative_path(value: str) -> str:
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts or "\\" in value or value.startswith("~"):
        raise SkillManifestError("manifest paths must be relative and traversal-free")
    return value


def digest_files(root: str, *, exclude: Sequence[str] = (MANIFEST_FILENAME,)) -> str:
    """Hash sorted relative file names and bytes; symlinks and traversal are rejected."""
    base = Path(root).expanduser().resolve()
    if not base.is_dir():
        raise SkillManifestError("skill root must be a directory")
    entries = []
    excluded = set(exclude)
    for path in sorted(base.rglob("*")):
        if path.is_symlink():
            raise SkillManifestError("symlinks are forbidden in skill bundles")
        if not path.is_file():
            continue
        relative = path.relative_to(base).as_posix()
        _validate_relative_path(relative)
        if relative in excluded:
            continue
        entries.append((relative, path.read_bytes()))
    hasher = hashlib.sha256()
    for relative, content in entries:
        name = relative.encode("utf-8")
        hasher.update(len(name).to_bytes(8, "big"))
        hasher.update(name)
        hasher.update(len(content).to_bytes(8, "big"))
        hasher.update(content)
    return "sha256:" + hasher.hexdigest()


@dataclass(frozen=True)
class SkillManifest:
    skill_id: str
    name: str
    version: str
    digest: str
    capabilities: Tuple[str, ...]
    platforms: Tuple[str, ...]
    provenance: Mapping[str, Any]
    entrypoint: Optional[str] = None
    format_version: str = MANIFEST_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != MANIFEST_FORMAT_VERSION:
            raise SkillManifestError("unsupported manifest format version")
        for field_name, value in (("skill_id", self.skill_id), ("name", self.name), ("version", self.version), ("digest", self.digest)):
            if not isinstance(value, str) or not value.strip():
                raise SkillManifestError("%s is required" % field_name)
        if not self.skill_id.replace("-", "").replace("_", "").isalnum():
            raise SkillManifestError("skill_id contains unsafe characters")
        if not self.digest.startswith("sha256:") or len(self.digest) != 71:
            raise SkillManifestError("digest must be sha256:<64 hex characters>")
        try:
            int(self.digest[7:], 16)
        except ValueError:
            raise SkillManifestError("digest must be hexadecimal")
        capabilities = tuple(dict.fromkeys(self.capabilities))
        if any(capability not in ALLOWED_CAPABILITIES for capability in capabilities):
            raise SkillManifestError("unsupported skill capability")
        platforms = tuple(dict.fromkeys(self.platforms))
        if not platforms or any(platform not in ALLOWED_PLATFORMS for platform in platforms):
            raise SkillManifestError("unsupported skill platform")
        if self.entrypoint is not None:
            _validate_relative_path(self.entrypoint)
        _reject_secret_keys(self.provenance)
        if not isinstance(self.provenance, Mapping) or "source" not in self.provenance:
            raise SkillManifestError("provenance.source is required")

    def to_dict(self) -> Mapping[str, Any]:
        data = {
            "format_version": self.format_version,
            "skill_id": self.skill_id,
            "name": self.name,
            "version": self.version,
            "digest": self.digest,
            "capabilities": list(self.capabilities),
            "platforms": list(self.platforms),
            "provenance": dict(self.provenance),
        }
        if self.entrypoint is not None:
            data["entrypoint"] = self.entrypoint
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"

    @classmethod
    def from_json(cls, text: str) -> "SkillManifest":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise SkillManifestError("manifest is not valid JSON: %s" % exc.msg)
        if not isinstance(data, Mapping):
            raise SkillManifestError("manifest root must be an object")
        allowed = {"format_version", "skill_id", "name", "version", "digest", "capabilities", "platforms", "provenance", "entrypoint"}
        unknown = sorted(set(data) - allowed)
        if unknown:
            raise SkillManifestError("unknown manifest field: %s" % unknown[0])
        for required in ("format_version", "skill_id", "name", "version", "digest", "capabilities", "platforms", "provenance"):
            if required not in data:
                raise SkillManifestError("missing manifest field: %s" % required)
        if not isinstance(data["capabilities"], list) or not isinstance(data["platforms"], list):
            raise SkillManifestError("capabilities and platforms must be arrays")
        return cls(format_version=str(data["format_version"]), skill_id=str(data["skill_id"]), name=str(data["name"]), version=str(data["version"]), digest=str(data["digest"]), capabilities=tuple(str(item) for item in data["capabilities"]), platforms=tuple(str(item) for item in data["platforms"]), provenance=data["provenance"], entrypoint=str(data["entrypoint"]) if data.get("entrypoint") is not None else None)

    @classmethod
    def from_file(cls, path: str) -> "SkillManifest":
        manifest_path = Path(path).expanduser().resolve()
        if manifest_path.name != MANIFEST_FILENAME:
            raise SkillManifestError("manifest filename must be %s" % MANIFEST_FILENAME)
        return cls.from_json(manifest_path.read_text(encoding="utf-8"))


__all__ = ["ALLOWED_CAPABILITIES", "ALLOWED_PLATFORMS", "MANIFEST_FILENAME", "MANIFEST_FORMAT_VERSION", "SkillManifest", "SkillManifestError", "digest_files"]

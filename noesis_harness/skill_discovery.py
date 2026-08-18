"""Read-only, fail-closed discovery for reusable agent skills.

The discoverer reads SKILL.md metadata only. It never imports, executes, or
loads the instruction body into an execution path. Permission patterns are
explicit and default to deny when a caller supplies a policy.
"""
from __future__ import annotations

import fnmatch
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_ALLOWED_FRONTMATTER = frozenset({"name", "description", "license", "compatibility", "metadata"})


class SkillDiscoveryError(ValueError):
    """Raised when a skill metadata file is malformed or unsafe."""


@dataclass(frozen=True)
class SkillDescriptor:
    name: str
    description: str
    path: str
    digest: str
    status: str
    reason: str = ""
    license: str = ""
    compatibility: str = ""

    def to_record(self) -> dict[str, str]:
        return {
            "name": self.name,
            "description": self.description,
            "path": self.path,
            "digest": self.digest,
            "status": self.status,
            "reason": self.reason,
            "license": self.license,
            "compatibility": self.compatibility,
        }


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise SkillDiscoveryError("frontmatter_required")
    try:
        end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration as exc:
        raise SkillDiscoveryError("frontmatter_unclosed") from exc
    metadata: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise SkillDiscoveryError("frontmatter_line_invalid")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key not in _ALLOWED_FRONTMATTER:
            raise SkillDiscoveryError("frontmatter_field_not_allowed:%s" % key)
        if key in metadata:
            raise SkillDiscoveryError("frontmatter_duplicate:%s" % key)
        metadata[key] = value
    return metadata, "\n".join(lines[end + 1 :]).lstrip()


def _validate_metadata(directory: Path, metadata: Mapping[str, str]) -> tuple[str, str, str, str]:
    name = str(metadata.get("name", ""))
    description = str(metadata.get("description", ""))
    if not _NAME.fullmatch(name) or name != directory.name:
        raise SkillDiscoveryError("skill_name_invalid_or_directory_mismatch")
    if not description or len(description) > 1024:
        raise SkillDiscoveryError("skill_description_invalid")
    return name, description, str(metadata.get("license", "")), str(metadata.get("compatibility", ""))


def _permission(name: str, permissions: Mapping[str, str] | None) -> tuple[str, str]:
    if permissions is None:
        return "visible", "no_policy"
    decision = "deny"
    matched = "default"
    for pattern, value in permissions.items():
        if fnmatch.fnmatchcase(name, str(pattern)):
            if value not in {"allow", "deny", "ask"}:
                raise SkillDiscoveryError("permission_value_invalid:%s" % value)
            decision, matched = value, str(pattern)
    return decision, "permission:%s" % matched


def discover(roots: Sequence[str], permissions: Mapping[str, str] | None = None) -> tuple[SkillDescriptor, ...]:
    """Discover valid skills under roots in deterministic path order.

    Invalid entries are returned as denied descriptors rather than skipped, so
    an operator can explain why a candidate was not exposed to the agent.
    """
    candidates: list[Path] = []
    for root_value in roots:
        root = Path(root_value).expanduser().resolve()
        if not root.exists():
            continue
        if root.is_file() and root.name == "SKILL.md":
            candidates.append(root)
        elif root.is_dir():
            candidates.extend(path for path in root.rglob("SKILL.md") if path.is_file() and not path.is_symlink())
    descriptors: list[SkillDescriptor] = []
    for path in sorted(set(candidates), key=lambda item: str(item)):
        digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        try:
            metadata, _body = _parse_frontmatter(path.read_text(encoding="utf-8"))
            name, description, license_name, compatibility = _validate_metadata(path.parent, metadata)
            status, reason = _permission(name, permissions)
            descriptors.append(SkillDescriptor(name, description, str(path), digest, status, reason, license_name, compatibility))
        except (OSError, UnicodeError, SkillDiscoveryError) as exc:
            descriptors.append(SkillDescriptor(path.parent.name, "", str(path), digest, "deny", str(exc)))
    return tuple(descriptors)


__all__ = ["SkillDescriptor", "SkillDiscoveryError", "discover"]

"""Registry versus disk reconciliation with drift/orphan detection.

Ported patterns from wshobson/agents:
- tools/doc_gardener.py: orphan / missing / stale checks against a registry.
- tools/validate_generated.py: Finding(severity, harness, path, message,
  remediation), where every finding carries a remediation string.
- generate.py --prune: an explicit orphan sweep plan.

This module is read-only with respect to the filesystem. It only produces
findings; it never creates or deletes artifacts. The only category marked
as safe to prune is ORPHAN, and pruning still requires a caller to act.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, List, Tuple

__all__ = [
    "Severity",
    "Finding",
    "reconcile_registry",
    "reconcile_directories",
    "prune_plan",
    "summarize",
]


class Severity(str, Enum):
    """Finding severity, ordered ERROR > WARNING > INFO."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


_SEVERITY_RANK = {
    Severity.ERROR: 2,
    Severity.WARNING: 1,
    Severity.INFO: 0,
}

_ORPHAN_REMEDIATION = "prune the orphan artifact or register it"
_MISSING_REMEDIATION = (
    "create the missing artifact at {0} or remove the registry entry"
)


def _require_text(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("{0} must be a non-empty string".format(field))


@dataclass(frozen=True)
class Finding:
    """A single reconciliation finding with an actionable remediation."""

    severity: Severity
    path: str
    message: str
    remediation: str

    def __post_init__(self):
        _require_text(self.message, "message")
        _require_text(self.remediation, "remediation")
        _require_text(self.path, "path")


def _normalize(path: str) -> str:
    """Case-insensitive, separator-insensitive comparison key for a path."""
    normalized = path.replace("\\", "/")
    while normalized.endswith("/"):
        normalized = normalized[:-1]
    return normalized.lower()


def _sort_key(finding: Finding) -> Tuple[int, str, str]:
    return (
        -_SEVERITY_RANK[finding.severity],
        finding.path,
        finding.message,
    )


def _ordered_unique(items: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def reconcile_registry(
    declared: Dict[str, str], actual: Iterable[str]
) -> List[Finding]:
    """Reconcile a logical-name -> path registry against paths on disk.

    declared: maps logical name to its registry path.
    actual: the set of paths present on disk.

    Emits MISSING (ERROR), ORPHAN (WARNING), DUPLICATE (WARNING) and
    MISMATCH (INFO) findings. Output is sorted by severity, then path.
    """
    findings: List[Finding] = []

    declared_items = sorted(declared.items(), key=lambda item: (item[0], item[1]))
    actual_list = _ordered_unique(sorted(actual))

    actual_keys = set(_normalize(path) for path in actual_list)
    declared_keys = set(_normalize(path) for path in declared.values())

    for name, path in declared_items:
        if _normalize(path) not in actual_keys:
            findings.append(
                Finding(
                    severity=Severity.ERROR,
                    path=path,
                    message=(
                        "declared artifact '{0}' is missing from disk at '{1}'"
                    ).format(name, path),
                    remediation=_MISSING_REMEDIATION.format(path),
                )
            )

    for path in actual_list:
        if _normalize(path) not in declared_keys:
            findings.append(
                Finding(
                    severity=Severity.WARNING,
                    path=path,
                    message="orphan artifact '{0}' is on disk but not declared".format(
                        path
                    ),
                    remediation=_ORPHAN_REMEDIATION,
                )
            )

    literal_groups: Dict[str, List[str]] = {}
    for name, path in declared_items:
        literal_groups.setdefault(path, []).append(name)
    for path in sorted(literal_groups):
        names = sorted(literal_groups[path])
        if len(names) > 1:
            findings.append(
                Finding(
                    severity=Severity.WARNING,
                    path=path,
                    message="path '{0}' is declared by multiple names: {1}".format(
                        path, ", ".join(names)
                    ),
                    remediation="assign a unique path",
                )
            )

    normalized_groups: Dict[str, List[str]] = {}
    for path in declared.values():
        normalized_groups.setdefault(_normalize(path), []).append(path)
    for key in sorted(normalized_groups):
        spellings = sorted(set(normalized_groups[key]))
        if len(spellings) > 1:
            findings.append(
                Finding(
                    severity=Severity.INFO,
                    path=key,
                    message=(
                        "path spelling differs only by case or separator: {0}"
                    ).format(", ".join(spellings)),
                    remediation="normalize path spelling",
                )
            )

    findings.sort(key=_sort_key)
    return findings


def reconcile_directories(root: str, expected: Dict[str, str]) -> List[Finding]:
    """Read-only reconcile of the immediate children of ``root``.

    Lists direct child names of ``root`` (no recursion, no writes) and
    reconciles them against ``expected``. A missing or non-directory root
    yields a single ERROR finding. Nothing is ever created or deleted.
    """
    if not os.path.isdir(root):
        return [
            Finding(
                severity=Severity.ERROR,
                path=root,
                message=(
                    "root directory '{0}' does not exist or is not a directory"
                ).format(root),
                remediation=_MISSING_REMEDIATION.format(root),
            )
        ]
    try:
        children = os.listdir(root)
    except OSError as exc:
        return [
            Finding(
                severity=Severity.ERROR,
                path=root,
                message="root directory '{0}' could not be read: {1}".format(root, exc),
                remediation=(
                    "ensure the directory at {0} is readable, then rerun the "
                    "reconciliation"
                ).format(root),
            )
        ]
    return reconcile_registry(expected, children)


def prune_plan(findings: Iterable[Finding]) -> List[str]:
    """Return sorted unique ORPHAN paths only (the safe-to-prune category)."""
    orphans = set()
    for finding in findings:
        if finding.severity != Severity.WARNING:
            continue
        is_orphan = (
            finding.remediation == _ORPHAN_REMEDIATION
            or "orphan" in finding.message.lower()
        )
        if is_orphan:
            orphans.add(finding.path)
    return sorted(orphans)


def summarize(findings: Iterable[Finding]) -> Dict[str, int]:
    """Count findings per severity value, plus a total."""
    counts = {
        Severity.ERROR.value: 0,
        Severity.WARNING.value: 0,
        Severity.INFO.value: 0,
        "total": 0,
    }
    for finding in findings:
        counts[finding.severity.value] += 1
        counts["total"] += 1
    return counts

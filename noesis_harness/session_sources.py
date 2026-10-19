"""Data-driven harness/session-source adapter registry.

Provenance: ported from the Go repository deja-vu, package
``internal/sources/registry.go``. deja-vu stores each supported agent
session format as one declarative record so that discovery, cold parse and
incremental parse are a single addition instead of three scattered switches.

This module is intentionally free of real filesystem access: the
``HarnessSpec.files`` provider is injected by the caller, and every
``FileKind.parse`` / ``FileKind.parse_from`` callable is supplied at
registration time. Only stdlib types are used.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class FileKind:
    """One session file format inside a harness.

    ``match`` decides whether a path belongs to this format. ``parse``
    performs the cold (full) parse. ``parse_from`` optionally performs an
    incremental parse that resumes from a byte/record offset; when it is
    ``None`` the format is not appendable.
    """

    name: str
    match: Callable[[str], bool]
    parse: Callable[..., Dict]
    parse_from: Optional[Callable[..., Dict]] = None


@dataclass(frozen=True)
class HarnessSpec:
    """A harness and the session file formats it understands.

    ``files`` is a caller-injected provider returning candidate paths; this
    module never touches the filesystem itself.
    """

    name: str
    files: Callable[[], List[str]]
    kinds: List[FileKind] = field(default_factory=list)


class SessionSourceRegistry:
    """In-memory registry of harness specs and their file kinds.

    Discovery, matching and parsing are all derived from the registered
    records. Harness iteration is always sorted so behavior is deterministic
    regardless of registration order.
    """

    def __init__(self) -> None:
        self._harnesses: Dict[str, HarnessSpec] = {}

    def register(self, spec: HarnessSpec) -> None:
        """Register one harness spec; a duplicate name is rejected."""
        if spec.name in self._harnesses:
            raise ValueError("duplicate harness name: %s" % spec.name)
        self._harnesses[spec.name] = spec

    def harnesses(self) -> List[str]:
        """Registered harness names, sorted."""
        return sorted(self._harnesses)

    def _kinds(self, spec: HarnessSpec):
        return list(spec.kinds)

    def _match(self, spec: HarnessSpec, path: str) -> Optional[FileKind]:
        for kind in spec.kinds:
            try:
                if kind.match(path):
                    return kind
            except Exception:
                continue
        return None

    def discover(self) -> List[Tuple[str, str, str]]:
        """Return ``(harness_name, kind_name, path)`` for every matched path.

        Results are sorted by ``(harness, path)``. Paths reported by the
        injected provider that match no kind are skipped. Duplicate paths are
        collapsed.
        """
        rows: List[Tuple[str, str, str]] = []
        for harness_name in self.harnesses():
            spec = self._harnesses[harness_name]
            try:
                paths = list(spec.files())
            except Exception:
                paths = []
            for path in sorted(set(paths)):
                kind = self._match(spec, path)
                if kind is not None:
                    rows.append((harness_name, kind.name, path))
        return sorted(rows, key=lambda row: (row[0], row[2]))

    def kind_for_path(self, path: str) -> Optional[Tuple[str, str]]:
        """Return ``(harness_name, kind_name)`` for the first matching kind.

        Harnesses are considered in sorted harness order; kinds within a
        harness are considered in registration order. Returns ``None`` when
        no registered kind matches.
        """
        for harness_name in self.harnesses():
            spec = self._harnesses[harness_name]
            kind = self._match(spec, path)
            if kind is not None:
                return (harness_name, kind.name)
        return None

    def parse_path(self, path: str) -> Dict:
        """Parse ``path`` with the matched kind's cold parser.

        Raises ``KeyError`` when no registered kind matches. The returned
        mapping is a copy stamped with ``harness`` and ``kind`` when those
        keys are absent.
        """
        found = self.kind_for_path(path)
        if found is None:
            raise KeyError("no session source kind for path: %s" % path)
        harness_name, kind_name = found
        spec = self._harnesses[harness_name]
        kind = self._match(spec, path)
        result = dict(kind.parse(path))
        result.setdefault("harness", harness_name)
        result.setdefault("kind", kind_name)
        return result

    def parse_appended(self, path: str) -> Dict:
        """Incrementally parse ``path`` from offset 0 via ``parse_from``.

        Raises ``KeyError`` when no registered kind matches and
        ``ValueError`` when the matched kind declares no incremental parser.
        """
        found = self.kind_for_path(path)
        if found is None:
            raise KeyError("no session source kind for path: %s" % path)
        harness_name, kind_name = found
        spec = self._harnesses[harness_name]
        kind = self._match(spec, path)
        if kind.parse_from is None:
            raise ValueError("kind is not appendable: %s" % kind.name)
        return kind.parse_from(path, 0)

    def appendable_kinds(self) -> List[Tuple[str, str]]:
        """Sorted ``(harness_name, kind_name)`` pairs that declare parse_from."""
        rows: List[Tuple[str, str]] = []
        for harness_name in self.harnesses():
            spec = self._harnesses[harness_name]
            for kind in spec.kinds:
                if kind.parse_from is not None:
                    rows.append((harness_name, kind.name))
        return sorted(rows)


REGISTRY = SessionSourceRegistry()


def register_harness(spec: HarnessSpec) -> None:
    """Register ``spec`` on the module-level :data:`REGISTRY`."""
    REGISTRY.register(spec)


def kind_for_path(path: str) -> Optional[Tuple[str, str]]:
    """Look up ``path`` on the module-level :data:`REGISTRY`."""
    return REGISTRY.kind_for_path(path)


__all__ = [
    "FileKind",
    "HarnessSpec",
    "REGISTRY",
    "SessionSourceRegistry",
    "kind_for_path",
    "register_harness",
]

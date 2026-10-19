"""Durable three-section loop state: Spec / Current understanding / Timeline.

Provenance: ported pattern from the ``AI-Builder-Club/skills`` repository
(``skills/seo-growth/assets/operationalize.md`` and ``seo-loop-template.md``).
That template keeps a loop's durable memory in three sections so each run
compounds instead of starting over: a stable ``Spec``, a ``Current
understanding`` block (baselines, verified non-problems, ruled-out candidates,
a ledger of applied changes, and gotchas), and an append-only ``Timeline``.
The driving observation is that "a loop that re-derives its conclusions every
run is just an expensive cron job".

This module is a local, stdlib-only interpretation of that pattern. It is pure
and deterministic apart from the explicitly requested file writes in
``LoopStateStore``. It does not call a model, and it does not schedule work;
it only records what a loop already knows so the next run can build on it.

Design notes:
  - ``Understanding`` holds the durable lists. Every list mutation goes through
    a helper that strips whitespace, rejects empty input, deduplicates, and
    sorts, so the rendered state is byte-stable regardless of insertion order.
  - ``LoopState.timeline`` is deliberately append-only and never deduplicated
    or sorted: history is allowed to repeat itself.
  - ``render`` emits deterministic Markdown with a ``kind: loop-state``
    frontmatter block; ``parse`` is a tolerant inverse of ``render``.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from noesis_harness.atomic_write import atomic_write_text, read_text
from noesis_harness.frontmatter import parse_frontmatter, yaml_scalar

__all__ = [
    "LoopStateError",
    "Understanding",
    "LoopState",
    "LoopStateStore",
]

_EM_DASH = "\u2014"
_KIND = "loop-state"
_FILENAME_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")


class LoopStateError(RuntimeError):
    """Raised when loop state is malformed or a mutation is invalid."""


def _clean(text: str, what: str) -> str:
    """Normalize one free-text value, rejecting empty or non-string input."""
    if not isinstance(text, str):
        raise LoopStateError("%s must be a str" % what)
    cleaned = " ".join(text.split())
    if not cleaned:
        raise LoopStateError("%s must be non-empty" % what)
    return cleaned


def _add_sorted(target: List[str], text: str) -> bool:
    """Deduplicate-insert ``text`` into ``target`` and keep it sorted.

    Returns ``True`` when the value was newly added and ``False`` when it was
    already present. The caller-visible boolean makes it cheap to detect a
    loop that keeps rediscovering the same non-problem.
    """
    value = _clean(text, "entry")
    if value in target:
        return False
    target.append(value)
    target.sort()
    return True


@dataclass
class Understanding:
    """The durable, compounding half of a loop's memory.

    Baselines are named measurements; the four lists are sorted and
    deduplicated. Directly appending to a list bypasses the invariant, so all
    intended mutation goes through the ``add_*`` methods.
    """

    baselines: Dict[str, float] = field(default_factory=dict)
    verified_non_problems: List[str] = field(default_factory=list)
    ruled_out: List[str] = field(default_factory=list)
    applied_changes: List[str] = field(default_factory=list)
    gotchas: List[str] = field(default_factory=list)

    def set_baseline(self, metric: str, value: float) -> None:
        """Record ``metric`` -> ``value``, overwriting any earlier baseline."""
        key = _clean(metric, "metric")
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            raise LoopStateError("baseline value for %r must be numeric" % key)
        self.baselines[key] = numeric

    def add_non_problem(self, text: str) -> bool:
        """Record something checked and found healthy; False if duplicate."""
        return _add_sorted(self.verified_non_problems, text)

    def add_ruled_out(self, text: str) -> bool:
        """Record a candidate ruled out; False if already recorded."""
        return _add_sorted(self.ruled_out, text)

    def record_change(self, text: str) -> bool:
        """Record an applied change in the ledger; False if duplicate."""
        return _add_sorted(self.applied_changes, text)

    def add_gotcha(self, text: str) -> bool:
        """Record a sharp edge worth remembering; False if duplicate."""
        return _add_sorted(self.gotchas, text)


class LoopState:
    """A named loop's durable three-section memory."""

    def __init__(self, name: str, spec: str = "") -> None:
        if not isinstance(name, str) or not name.strip():
            raise LoopStateError("name must be a non-empty str")
        cleaned_name = name.strip()
        if "\n" in cleaned_name or "\r" in cleaned_name:
            raise LoopStateError("name must not contain newlines")
        self.name = cleaned_name
        self.spec = spec if isinstance(spec, str) else str(spec)
        self.understanding = Understanding()
        self._timeline: List[str] = []

    def set_spec(self, spec: str) -> None:
        """Replace the stable spec text for this loop."""
        if not isinstance(spec, str):
            raise LoopStateError("spec must be a str")
        self.spec = spec

    def set_baseline(self, metric: str, value: float) -> None:
        """Delegate to the understanding baseline setter."""
        self.understanding.set_baseline(metric, value)

    def add_non_problem(self, text: str) -> bool:
        return self.understanding.add_non_problem(text)

    def add_ruled_out(self, text: str) -> bool:
        return self.understanding.add_ruled_out(text)

    def record_change(self, text: str) -> bool:
        return self.understanding.record_change(text)

    def add_gotcha(self, text: str) -> bool:
        return self.understanding.add_gotcha(text)

    def append_timeline(self, date: str, source: str, text: str) -> str:
        """Append one immutable history line and return its formatted form.

        The line shape is ``<date> | <source> \u2014 <text>``. Timeline entries
        are never deduplicated or reordered; two identical events at two
        different times are two events.
        """
        stamp = _clean(date, "date")
        origin = _clean(source, "source")
        detail = _clean(text, "timeline text")
        line = "%s | %s %s %s" % (stamp, origin, _EM_DASH, detail)
        self._timeline.append(line)
        return line

    def timeline(self) -> List[str]:
        """Return a copy of the append-only timeline."""
        return list(self._timeline)

    def render(self) -> str:
        """Render deterministic Markdown with a ``kind: loop-state`` header."""
        understanding = self.understanding
        lines: List[str] = [
            "---",
            "kind: %s" % _KIND,
            "name: %s" % yaml_scalar(self.name),
            "frequency: %d" % len(self._timeline),
            "---",
            "",
            "## Spec",
            "",
        ]
        if self.spec.strip():
            lines.append(self.spec.strip())
            lines.append("")
        lines.extend(
            [
                "## Current understanding",
                "",
                "### Baselines",
                "",
            ]
        )
        for key in sorted(understanding.baselines):
            lines.append(
                "- %s: %s" % (key, yaml_scalar(understanding.baselines[key]))
            )
        lines.append("")
        for title, values in (
            ("### Verified non-problems", understanding.verified_non_problems),
            ("### Ruled out", understanding.ruled_out),
            ("### Applied changes", understanding.applied_changes),
            ("### Gotchas", understanding.gotchas),
        ):
            lines.append(title)
            lines.append("")
            for value in values:
                lines.append("- %s" % value)
            lines.append("")
        lines.append("## Timeline")
        lines.append("")
        for entry in self._timeline:
            lines.append("- %s" % entry)
        lines.append("")
        return "\n".join(lines)

    @classmethod
    def parse(cls, text: str) -> "LoopState":
        """Tolerantly rebuild a ``LoopState`` from ``render`` output."""
        if not isinstance(text, str):
            raise LoopStateError("parse expects a str")
        fields, body = parse_frontmatter(text)
        raw_name = fields.get("name") or fields.get("Name") or ""
        if not isinstance(raw_name, str):
            raw_name = str(raw_name)
        name = raw_name.strip() or "unnamed"

        state = cls(name)
        sections = _split_headings(body.split("\n"), "## ")
        state.set_spec("\n".join(sections.get("Spec", [])).strip())

        understanding_blocks = _split_headings(
            sections.get("Current understanding", []), "### "
        )
        understanding = state.understanding
        for item in _bullets(understanding_blocks.get("Baselines", [])):
            key, sep, raw = item.partition(":")
            if not sep:
                continue
            try:
                understanding.baselines[key.strip()] = float(raw.strip())
            except ValueError:
                continue
        understanding.verified_non_problems[:] = _sorted_unique(
            _bullets(understanding_blocks.get("Verified non-problems", []))
        )
        understanding.ruled_out[:] = _sorted_unique(
            _bullets(understanding_blocks.get("Ruled out", []))
        )
        understanding.applied_changes[:] = _sorted_unique(
            _bullets(understanding_blocks.get("Applied changes", []))
        )
        understanding.gotchas[:] = _sorted_unique(
            _bullets(understanding_blocks.get("Gotchas", []))
        )

        state._timeline[:] = _bullets(sections.get("Timeline", []))
        return state

    def digest(self) -> str:
        """Return a ``sha256:`` content digest of the rendered state."""
        payload = self.render().encode("utf-8")
        return "sha256:" + hashlib.sha256(payload).hexdigest()


def _split_headings(lines: List[str], marker: str) -> Dict[str, List[str]]:
    """Group lines under headings that start with ``marker``."""
    sections: Dict[str, List[str]] = {}
    current: Optional[str] = None
    buffer: List[str] = []
    for line in lines:
        if line.startswith(marker):
            if current is not None:
                sections[current] = buffer
            current = line[len(marker):].strip()
            buffer = []
        elif current is not None:
            buffer.append(line)
    if current is not None:
        sections[current] = buffer
    return sections


def _bullets(lines: List[str]) -> List[str]:
    """Return the text of ``- item`` lines, stripped and non-empty."""
    items: List[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        value = stripped[2:].strip()
        if value:
            items.append(value)
    return items


def _sorted_unique(values: List[str]) -> List[str]:
    """Sort and deduplicate a list of strings deterministically."""
    return sorted(set(values))


class LoopStateStore:
    """Filesystem store for ``LoopState`` documents.

    Each state is written to ``<root>/<safe-name>.md`` using the shared atomic
    writer (unique temp sibling plus ``os.replace``), so readers never observe
    a partially written file.
    """

    def __init__(self, root: str) -> None:
        if not isinstance(root, str) or not root.strip():
            raise LoopStateError("root must be a non-empty str")
        self.root = root

    def _path(self, name: str) -> str:
        return os.path.join(self.root, _safe_filename(name) + ".md")

    def save(self, state: LoopState) -> str:
        """Atomically write ``state`` and return the file path."""
        if not isinstance(state, LoopState):
            raise LoopStateError("save expects a LoopState")
        os.makedirs(self.root, exist_ok=True)
        path = self._path(state.name)
        atomic_write_text(path, state.render())
        return path

    def load(self, name: str) -> Optional[LoopState]:
        """Load a state by name, or return ``None`` when it is missing."""
        text = read_text(self._path(name))
        if text is None:
            return None
        try:
            return LoopState.parse(text)
        except LoopStateError:
            return None

    def names(self) -> List[str]:
        """Return the sorted state names present in the store."""
        if not os.path.isdir(self.root):
            return []
        found: List[str] = []
        for entry in os.listdir(self.root):
            if not entry.endswith(".md"):
                continue
            if not os.path.isfile(os.path.join(self.root, entry)):
                continue
            found.append(entry[: -len(".md")])
        return sorted(found)


def _safe_filename(name: str) -> str:
    """Reduce a state name to a filesystem-safe stem."""
    if not isinstance(name, str):
        name = str(name)
    stem = _FILENAME_SAFE_RE.sub("_", name.strip())
    stem = stem.lstrip(".")
    if not stem:
        stem = "unnamed"
    return stem

"""Loop contracts: a domain with a charter, a cadence, and produced artifacts.

Provenance: ported from the ``AI-Builder-Club/skills`` repository, in
particular ``skills/new-loop/SKILL.md`` and
``references/KNOWLEDGE_SETUP.md``. That pattern describes one loop as a
separable workstream documented by a small frontmatter block
(``kind: domain``, ``domain``, ``status: active|paused|archived``, ``goal``,
``cadence``) plus fixed Markdown sections (``## Current focus``,
``## Backlog``, ``## Evidence & analysis``, ``## Metrics``, ``## Timeline``).
An explicit numeric gate condition can flip a loop from its base cadence into
another cadence once a threshold is met.

This module keeps the same spirit but stays dependency-free: the frontmatter
is a hand-rolled ``key: value`` header (no YAML parser), lists render inline as
``[a, b]``, and gate conditions are encoded as compact single tokens. Only the
Python standard library is used (``re``, ``operator``, ``dataclasses``,
``enum``, ``typing``). The module is pure and deterministic: no I/O, no global
state, no clock.

Limitations (documented, fail-safe):
  - Scalar values containing newlines are not preserved by the frontmatter
    round trip; keep ``goal`` and gate metrics on a single line.
  - ``GateCondition.evaluate`` is fail-closed: a metric that is absent from the
    supplied mapping evaluates to ``False`` rather than raising.
"""

from __future__ import annotations

import operator
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

__all__ = [
    "Cadence",
    "LoopStatus",
    "GateCondition",
    "LoopContract",
    "LoopRegistry",
    "kebab_case",
]


class Cadence(str, Enum):
    """How often a loop is expected to run."""

    MANUAL = "manual"
    DAILY = "daily"
    WEEKLY = "weekly"
    CRON = "cron"


class LoopStatus(str, Enum):
    """Lifecycle state of a loop."""

    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


_KEBAB_SPLIT_RE = re.compile(r"([a-z0-9])([A-Z])")
_KEBAB_CLEAN_RE = re.compile(r"[^a-z0-9]+")

_VALID_OPS = (">=", "<=", ">", "<", "==")

_OPS = {
    ">=": operator.ge,
    "<=": operator.le,
    ">": operator.gt,
    "<": operator.lt,
    "==": operator.eq,
}


def kebab_case(value: str) -> str:
    """Return ``value`` folded into lower-case kebab-case.

    CamelCase boundaries are split, every run of non-alphanumeric characters
    becomes a single hyphen, and leading/trailing hyphens are removed. The
    result is deterministic and idempotent for already-kebab inputs.
    """
    text = str(value)
    text = _KEBAB_SPLIT_RE.sub(r"\1-\2", text)
    text = text.lower()
    text = _KEBAB_CLEAN_RE.sub("-", text)
    return text.strip("-")


def _coerce_cadence(value) -> "Cadence":
    """Coerce ``value`` (Cadence or case-insensitive string) to Cadence."""
    if isinstance(value, Cadence):
        return value
    return Cadence(str(value).strip().lower())


def _coerce_status(value) -> "LoopStatus":
    """Coerce ``value`` (LoopStatus or case-insensitive string) to LoopStatus."""
    if isinstance(value, LoopStatus):
        return value
    return LoopStatus(str(value).strip().lower())


@dataclass(frozen=True)
class GateCondition:
    """A numeric gate that promotes a loop to ``target_cadence`` when met.

    ``op`` must be one of ``">="``, ``"<="``, ``">"``, ``"<"``, ``"=="``.
    ``threshold`` is stored as ``float`` and ``target_cadence`` as a
    :class:`Cadence` (a string is coerced).
    """

    metric: str
    op: str
    threshold: float
    target_cadence: Cadence

    def __post_init__(self) -> None:
        if self.op not in _VALID_OPS:
            raise ValueError(
                "invalid gate operator %r; expected one of %s"
                % (self.op, ", ".join(_VALID_OPS))
            )
        object.__setattr__(self, "threshold", float(self.threshold))
        if not isinstance(self.target_cadence, Cadence):
            object.__setattr__(
                self, "target_cadence", _coerce_cadence(self.target_cadence)
            )

    def evaluate(self, values: Dict[str, float]) -> bool:
        """Return True when the metric satisfies the gate.

        Fail-closed: when ``metric`` is missing from ``values`` (or its value
        is not numeric) the gate evaluates to ``False`` and never raises.
        """
        if self.metric not in values:
            return False
        try:
            actual = float(values[self.metric])
        except (TypeError, ValueError):
            return False
        return bool(_OPS[self.op](actual, self.threshold))


@dataclass
class LoopContract:
    """Charter for one separable workstream.

    A loop declares what it consumes, what artifacts it produces, its backlog,
    its current focus, and optional numeric gates that flip its cadence.
    """

    name: str
    goal: str
    cadence: Cadence = Cadence.MANUAL
    status: LoopStatus = LoopStatus.ACTIVE
    consumes: List[str] = field(default_factory=list)
    produces: List[str] = field(default_factory=list)
    backlog: List[str] = field(default_factory=list)
    current_focus: str = ""
    gates: List[GateCondition] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.cadence = _coerce_cadence(self.cadence)
        self.status = _coerce_status(self.status)

    def validate(self) -> List[str]:
        """Return human-readable problems; an empty list means valid."""
        problems: List[str] = []
        if not self.name or not self.name.strip():
            problems.append("name must not be empty")
        else:
            expected = kebab_case(self.name)
            if expected != self.name:
                problems.append(
                    "name %r is not kebab-case (expected %r)"
                    % (self.name, expected)
                )
        if not self.goal or not self.goal.strip():
            problems.append("goal must not be empty")
        if not self.produces:
            problems.append("produces must list at least one artifact")
        for index, gate in enumerate(self.gates):
            if not gate.metric or not gate.metric.strip():
                problems.append("gate %d has an empty metric" % index)
        return problems

    def add_backlog(self, item: str) -> None:
        """Append ``item`` to the end of the backlog."""
        self.backlog.append(item)

    def next_backlog(self) -> Optional[str]:
        """Return the front of the backlog without removing it, else None."""
        if not self.backlog:
            return None
        return self.backlog[0]

    def effective_cadence(self, values: Dict[str, float]) -> "Cadence":
        """Return the cadence implied by the first satisfied gate.

        Gates are checked in list order; the first satisfied gate wins. When no
        gate is satisfied (or there are none) the base cadence is returned.
        """
        for gate in self.gates:
            if gate.evaluate(values):
                return gate.target_cadence
        return self.cadence

    def to_frontmatter(self) -> str:
        """Render the contract as frontmatter plus fixed Markdown sections."""
        lines: List[str] = ["---"]
        lines.append("kind: domain")
        lines.append("domain: %s" % _emit_scalar(self.name))
        lines.append("status: %s" % self.status.value)
        lines.append("goal: %s" % _emit_scalar(self.goal))
        lines.append("cadence: %s" % self.cadence.value)
        lines.append("consumes: %s" % _emit_list(self.consumes))
        lines.append("produces: %s" % _emit_list(self.produces))
        lines.append(
            "gates: %s" % _emit_list([_emit_gate(gate) for gate in self.gates])
        )
        lines.append("---")
        lines.append("")
        lines.append("## Current focus")
        lines.append("")
        if self.current_focus:
            lines.append(self.current_focus)
        lines.append("")
        lines.append("## Backlog")
        lines.append("")
        for item in self.backlog:
            lines.append("- %s" % item)
        lines.append("")
        lines.append("## Evidence & analysis")
        lines.append("")
        lines.append("## Metrics")
        lines.append("")
        lines.append("## Timeline")
        lines.append("")
        return "\n".join(lines)

    @classmethod
    def from_frontmatter(cls, text: str) -> "LoopContract":
        """Parse a document produced by :meth:`to_frontmatter`.

        Tolerant of missing optional fields: absent keys fall back to the
        dataclass defaults. Malformed gate encodings raise ``ValueError``.
        """
        fields, body = _parse_header(text)
        sections = _parse_sections(body)

        name = fields.get("domain", fields.get("name", ""))
        goal = fields.get("goal", "")
        cadence = fields.get("cadence", Cadence.MANUAL.value)
        status = fields.get("status", LoopStatus.ACTIVE.value)
        consumes = _parse_list(fields.get("consumes", ""))
        produces = _parse_list(fields.get("produces", ""))
        gates = [_parse_gate(item) for item in _parse_list(fields.get("gates", ""))]

        current_focus = sections.get("Current focus", "")
        backlog_section = sections.get("Backlog")
        if backlog_section is None:
            backlog = _parse_list(fields.get("backlog", ""))
        else:
            backlog = _parse_backlog(backlog_section)

        return cls(
            name=name,
            goal=goal,
            cadence=cadence,
            status=status,
            consumes=consumes,
            produces=produces,
            backlog=backlog,
            current_focus=current_focus,
            gates=gates,
        )


class LoopRegistry:
    """An in-memory, name-keyed collection of loop contracts."""

    def __init__(self) -> None:
        self._contracts: Dict[str, LoopContract] = {}

    def register(self, contract: LoopContract) -> None:
        """Register ``contract``; raise ValueError on a duplicate name."""
        if not isinstance(contract, LoopContract):
            raise TypeError(
                "register expects LoopContract, got %s" % type(contract).__name__
            )
        if contract.name in self._contracts:
            raise ValueError("duplicate loop contract: %r" % contract.name)
        self._contracts[contract.name] = contract

    def names(self) -> List[str]:
        """Return all registered names, sorted."""
        return sorted(self._contracts)

    def active(self) -> List[LoopContract]:
        """Return active contracts ordered by name."""
        return [
            self._contracts[name]
            for name in sorted(self._contracts)
            if self._contracts[name].status == LoopStatus.ACTIVE
        ]

    def get(self, name: str) -> Optional[LoopContract]:
        """Return the contract registered under ``name``, else None."""
        return self._contracts.get(name)

    def by_cadence(self, cadence) -> List[str]:
        """Return names of contracts with ``cadence``, sorted."""
        wanted = _coerce_cadence(cadence)
        return [
            name
            for name in sorted(self._contracts)
            if self._contracts[name].cadence == wanted
        ]


_SCALAR_SPECIALS = frozenset(',[]#"\n\r')

_GATE_RE = re.compile(
    r"^(?P<metric>\S+)\s+(?P<op>==|>=|<=|>|<)\s+(?P<threshold>\S+)\s+@(?P<cadence>\S+)$"
)


def _emit_scalar(value: str) -> str:
    """Emit a scalar, double-quoting when it could confuse the parser."""
    text = str(value)
    if (
        text == ""
        or text != text.strip()
        or any(ch in _SCALAR_SPECIALS for ch in text)
    ):
        return '"' + text.replace('"', '""') + '"'
    return text


def _emit_list(items: List[str]) -> str:
    """Emit an inline ``[a, b]`` list with per-item scalar quoting."""
    return "[" + ", ".join(_emit_scalar(item) for item in items) + "]"


def _emit_gate(gate: GateCondition) -> str:
    """Encode a gate as ``metric op threshold @cadence``."""
    return "%s %s %s @%s" % (
        gate.metric,
        gate.op,
        gate.threshold,
        gate.target_cadence.value,
    )


def _parse_gate(text: str) -> GateCondition:
    """Decode a token produced by :func:`_emit_gate`."""
    match = _GATE_RE.match(text.strip())
    if match is None:
        raise ValueError("invalid gate encoding: %r" % text)
    return GateCondition(
        metric=match.group("metric"),
        op=match.group("op"),
        threshold=float(match.group("threshold")),
        target_cadence=_coerce_cadence(match.group("cadence")),
    )


def _split_inline(text: str) -> List[str]:
    """Split ``text`` on commas that are outside quotes."""
    parts: List[str] = []
    buf: List[str] = []
    quote: Optional[str] = None
    escaped = False
    for ch in text:
        if escaped:
            buf.append(ch)
            escaped = False
            continue
        if quote == '"' and ch == "\\":
            buf.append(ch)
            escaped = True
            continue
        if quote is not None:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ('"', "'"):
            quote = ch
            buf.append(ch)
            continue
        if ch == ",":
            parts.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    parts.append("".join(buf))
    return parts


def _unquote(text: str) -> str:
    """Strip one layer of matching quotes and unescape doubled quotes."""
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ('"', "'"):
        inner = text[1:-1]
        if text[0] == '"':
            inner = inner.replace('""', '"')
        else:
            inner = inner.replace("''", "'")
        return inner
    return text


def _parse_list(value: str) -> List[str]:
    """Parse ``[a, b]`` or a single scalar into a list of strings."""
    text = value.strip()
    if text == "":
        return []
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if inner == "":
            return []
        items: List[str] = []
        for part in _split_inline(inner):
            part = part.strip()
            if part == "":
                continue
            items.append(_unquote(part))
        return items
    return [_unquote(text)]


def _parse_header(text: str):
    """Split ``text`` into frontmatter fields and the remaining body."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    fields: Dict[str, str] = {}
    index = 0
    if lines and lines[0].strip() == "---":
        index = 1
        while index < len(lines):
            line = lines[index]
            if line.strip() == "---":
                index += 1
                break
            if ":" in line:
                key, _, raw = line.partition(":")
                fields[key.strip()] = raw.strip()
            index += 1
        body = "\n".join(lines[index:])
    else:
        body = text
    return fields, body


def _parse_sections(body: str) -> Dict[str, str]:
    """Collect the text under each ``## Heading`` until the next heading."""
    sections: Dict[str, str] = {}
    current: Optional[str] = None
    buf: List[str] = []
    for line in body.split("\n"):
        if line.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(buf).strip("\n")
            current = line[3:].strip()
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip("\n")
    return sections


def _parse_backlog(section: str) -> List[str]:
    """Parse ``- item`` lines from the backlog section."""
    items: List[str] = []
    for line in section.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- "):
            items.append(stripped[2:])
        elif stripped == "-":
            items.append("")
    return items

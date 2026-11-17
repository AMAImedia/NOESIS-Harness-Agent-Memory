"""noesis_harness/memory_index.py

Typed file-based memory records with a bounded auto-loaded index.

Borrowed patterns (provenance):
  - claude-code-book, Part-2 chapter 06 "Memory": four-type closed taxonomy
    (user / feedback / project / reference); one Markdown file per memory
    carrying YAML-ish frontmatter with ``name`` / ``description`` / ``type``;
    ``MEMORY.md`` as an index capped at MAX_ENTRYPOINT_LINES / MAX_ENTRYPOINT_BYTES
    with line-then-byte truncation; and path safety that rejects traversal,
    absolute, drive-letter and UNC names.

This module is stdlib-only and deterministic: it never writes to disk, never
calls an LLM, and performs no filesystem access. ``safe_memory_path`` computes
a sanitized join only; persistence is the caller's responsibility. The
frontmatter parser is self-contained and does NOT depend on any third-party or
sibling ``frontmatter`` module.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List

MAX_ENTRYPOINT_LINES = 200
MAX_ENTRYPOINT_BYTES = 25000
ENTRY_MAX_CHARS = 150


class MemoryType(str, Enum):
    """Closed taxonomy of memory record types."""

    USER = "user"
    FEEDBACK = "feedback"
    PROJECT = "project"
    REFERENCE = "reference"


class MemoryRecordError(ValueError):
    """Raised when a memory record or path is invalid."""


_DRIVE_RE = re.compile(r"^[A-Za-z]:")


def _quote_scalar(value: str) -> str:
    """Quote a frontmatter scalar when needed.

    A scalar is quoted when it contains a colon, a hash, a double quote, or
    leading/trailing whitespace. Embedded double quotes are escaped by
    doubling them.
    """
    needs_quote = (
        ":" in value
        or "#" in value
        or '"' in value
        or value != value.strip()
        or "\n" in value
        or value == ""
    )
    if not needs_quote:
        return value
    escaped = value.replace('"', '""')
    return '"' + escaped + '"'


def _unquote_scalar(value: str) -> str:
    """Reverse :func:`_quote_scalar` for a single frontmatter value."""
    value = value.strip()
    if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
        return value[1:-1].replace('""', '"')
    return value


@dataclass
class MemoryRecord:
    """A single typed memory with frontmatter metadata and a Markdown body."""

    name: str
    description: str
    type: MemoryType
    body: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise MemoryRecordError("memory name must be a non-empty string")
        if not isinstance(self.description, str) or not self.description.strip():
            raise MemoryRecordError("memory description must be a non-empty string")
        if isinstance(self.type, MemoryType):
            pass
        elif isinstance(self.type, str):
            try:
                self.type = MemoryType(self.type)
            except ValueError as exc:
                raise MemoryRecordError(
                    "unknown memory type: {0!r}".format(self.type)
                ) from exc
        else:
            raise MemoryRecordError(
                "memory type must be a MemoryType or its string value"
            )
        if not isinstance(self.body, str):
            raise MemoryRecordError("memory body must be a string")


def render_record(record: MemoryRecord) -> str:
    """Render a record as frontmatter plus body.

    The output shape is::

        ---
        name: ...
        description: ...
        type: ...
        ---

        <body>
    """
    lines = [
        "---",
        "name: " + _quote_scalar(record.name),
        "description: " + _quote_scalar(record.description),
        "type: " + record.type.value,
        "---",
        "",
        record.body,
    ]
    return "\n".join(lines)


def parse_record(text: str) -> MemoryRecord:
    """Parse the output of :func:`render_record` back into a record.

    Tolerant of a missing body and of an unquoted or quoted scalar. Raises
    :class:`MemoryRecordError` when frontmatter delimiters are missing or a
    required field is absent/invalid.
    """
    if not isinstance(text, str):
        raise MemoryRecordError("record text must be a string")
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise MemoryRecordError("missing frontmatter opening delimiter '---'")
    close = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            close = index
            break
    if close is None:
        raise MemoryRecordError("missing frontmatter closing delimiter '---'")

    fields = {}
    for raw in lines[1:close]:
        if not raw.strip():
            continue
        if ":" not in raw:
            raise MemoryRecordError("invalid frontmatter line: {0!r}".format(raw))
        key, _, value = raw.partition(":")
        key = key.strip()
        if key in fields:
            raise MemoryRecordError("duplicate frontmatter field: {0!r}".format(key))
        fields[key] = _unquote_scalar(value)

    for required in ("name", "description", "type"):
        if required not in fields or fields[required] == "":
            raise MemoryRecordError(
                "missing required frontmatter field: {0!r}".format(required)
            )

    body_lines = lines[close + 1:]
    if body_lines and body_lines[0] == "":
        body_lines = body_lines[1:]
    body = "\n".join(body_lines)

    return MemoryRecord(
        name=fields["name"],
        description=fields["description"],
        type=fields["type"],
        body=body,
    )


def _truncate_utf8(text: str, max_bytes: int) -> str:
    """Truncate *text* so its UTF-8 encoding fits *max_bytes* at a codepoint boundary."""
    if max_bytes <= 0:
        return ""
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    return encoded[:max_bytes].decode("utf-8", "ignore")


class MemoryIndex:
    """An in-memory collection of records with a bounded entrypoint renderer."""

    def __init__(self) -> None:
        self._records: Dict[str, MemoryRecord] = {}

    def add(self, record: MemoryRecord) -> None:
        """Add or replace a record by name (deterministic last-write-wins)."""
        if not isinstance(record, MemoryRecord):
            raise MemoryRecordError("add() expects a MemoryRecord")
        self._records[record.name] = record

    def entries(self) -> List[MemoryRecord]:
        """Return records sorted by (type value, name)."""
        return sorted(
            self._records.values(),
            key=lambda item: (item.type.value, item.name),
        )

    def types(self) -> Dict[str, int]:
        """Count records by type value, ordered by type value."""
        counts: Dict[str, int] = {}
        for record in self.entries():
            counts[record.type.value] = counts.get(record.type.value, 0) + 1
        return counts

    @staticmethod
    def _format_entry(record: MemoryRecord) -> str:
        clean_name = record.name.replace("\r", " ").replace("\n", " ")
        clean_desc = record.description.replace("\r", " ").replace("\n", " ")
        line = "- [{0}] {1} :: {2}".format(
            record.type.value, clean_name, clean_desc
        )
        if len(line) > ENTRY_MAX_CHARS:
            line = line[:ENTRY_MAX_CHARS]
        return line

    def rebuild(
        self,
        max_lines: int = MAX_ENTRYPOINT_LINES,
        max_bytes: int = MAX_ENTRYPOINT_BYTES,
    ) -> str:
        """Render the bounded index entrypoint.

        Entries are emitted one line per record. The line cap is applied
        first, then the UTF-8 byte cap at a codepoint boundary. When entries
        are dropped a truncation warning line ``# truncated: N entries
        omitted`` is appended, and the warning itself counts toward both caps.
        """
        if max_lines < 0:
            max_lines = 0
        if max_bytes < 0:
            max_bytes = 0

        records = self.entries()
        lines = [self._format_entry(record) for record in records]
        total = len(lines)

        joined = "\n".join(lines)
        if len(lines) <= max_lines and len(joined.encode("utf-8")) <= max_bytes:
            return joined

        kept = min(total, max(0, max_lines - 1))
        while kept > 0:
            omitted = total - kept
            warning = "# truncated: {0} entries omitted".format(omitted)
            candidate_lines = lines[:kept] + [warning]
            candidate = "\n".join(candidate_lines)
            if (
                len(candidate_lines) <= max_lines
                and len(candidate.encode("utf-8")) <= max_bytes
            ):
                return candidate
            kept -= 1

        if total == 0:
            return ""
        warning = "# truncated: {0} entries omitted".format(total)
        return _truncate_utf8(warning, max_bytes)

    def find(self, text: str) -> List[MemoryRecord]:
        """Case-insensitive substring search over name, description and body."""
        if not isinstance(text, str):
            raise MemoryRecordError("find() text must be a string")
        needle = text.lower()
        matches = []
        for record in self.entries():
            haystack = "\n".join((record.name, record.description, record.body))
            if needle in haystack.lower():
                matches.append(record)
        return matches


def safe_memory_path(base: str, name: str) -> str:
    """Join *name* under *base* after rejecting unsafe names.

    Rejects absolute paths, drive letters, UNC paths, ``..`` traversal, null
    bytes, and any name that would escape *base*. Performs no filesystem
    access and returns the normalized joined path.
    """
    if not isinstance(base, str) or not base.strip():
        raise MemoryRecordError("base path must be a non-empty string")
    if not isinstance(name, str) or not name.strip():
        raise MemoryRecordError("memory name must be a non-empty string")
    if "\x00" in name:
        raise MemoryRecordError("memory name must not contain null bytes")
    if name.startswith("\\\\") or name.startswith("//"):
        raise MemoryRecordError("UNC paths are not allowed: {0!r}".format(name))
    if _DRIVE_RE.match(name):
        raise MemoryRecordError("drive-letter paths are not allowed: {0!r}".format(name))
    if os.path.isabs(name):
        raise MemoryRecordError("absolute paths are not allowed: {0!r}".format(name))

    normalized_parts = re.split(r"[\\/]+", name)
    if any(part == ".." for part in normalized_parts):
        raise MemoryRecordError("path traversal is not allowed: {0!r}".format(name))

    base_norm = os.path.normpath(base)
    joined = os.path.normpath(os.path.join(base_norm, name))
    if joined != base_norm and not joined.startswith(base_norm + os.sep):
        raise MemoryRecordError("memory name escapes base: {0!r}".format(name))
    return joined


__all__ = [
    "MemoryType",
    "MemoryRecordError",
    "MemoryRecord",
    "MemoryIndex",
    "render_record",
    "parse_record",
    "safe_memory_path",
    "MAX_ENTRYPOINT_LINES",
    "MAX_ENTRYPOINT_BYTES",
    "ENTRY_MAX_CHARS",
]

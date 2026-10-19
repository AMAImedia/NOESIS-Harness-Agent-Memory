"""Shared persistent coordination board + structured task notifications.

Pattern ported from ``claude-code-book`` (Part-3, chapter 10):

  - "Scratchpad": a shared, session-isolated directory where cooperating
    agents drop durable artifacts instead of passing everything through the
    conversation. It is file-backed so a crashed session never loses state
    and any later session can re-read it.
  - The concurrency policy is ``read = parallel`` / ``write = per-file-set
    serial``: any number of readers may run at once, while writers touching
    the same file-set are serialized by a lock keyed on that set's name.
  - ``<task-note>``: a compact XML-ish envelope carrying
    ``task-id``, ``status``, ``summary``, ``result`` and ``usage``, used to
    report structured task outcomes between agents.
  - Confidence annotations ``[HIGH]`` / ``[MEDIUM]`` / ``[LOW]`` class a
    record by how much it can be trusted.

Design notes:

  - A board is a directory. Topics are append-only JSONL files named
    ``<topic>.jsonl``; file-sets are single files named after the set. Both
    are created lazily and neither is ever deleted by this module.
  - Publishing is idempotent by the canonical JSON digest of the record, so
    retrying a publish never duplicates a line.
  - Writing a file-set is idempotent by exact content, so re-publishing the
    same content preserves the existing file (and its stat identity).

This module is stdlib-only, Python 3.9 compatible, and deterministic. The
only side effects are the requested file writes.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

__all__ = [
    "Confidence",
    "TaskNotification",
    "SharedBoard",
    "WriteConflict",
    "safe_name",
]

_JSONL_SUFFIX = ".jsonl"
_NAME_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")
_ATTR_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_-]*)\s*=\s*\"([^\"]*)\"")


class Confidence(str, Enum):
    """How much trust a board record or notification carries."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class WriteConflict(RuntimeError):
    """Raised when a serialized board write cannot be completed safely."""


def safe_name(name: str) -> str:
    """Return a filesystem-safe flat name for a board topic or file-set.

    Rejects empty names and any name containing a path separator, a ``..``
    traversal segment, or a NUL byte. Remaining characters outside
    ``[A-Za-z0-9._-]`` are replaced with ``_``. The result never contains a
    directory component, so it can only ever address a direct child of the
    board root.
    """
    if not isinstance(name, str):
        raise TypeError("name must be str")
    if not name:
        raise ValueError("name must not be empty")
    if "\x00" in name:
        raise ValueError("name must not contain NUL")
    if name in (".", "..") or ".." in name:
        raise ValueError("name must not contain '..': %r" % (name,))
    for separator in (os.sep, os.altsep, "/", "\\"):
        if separator and separator in name:
            raise ValueError("name must not contain a path separator: %r" % (name,))
    cleaned = _NAME_SAFE_RE.sub("_", name)
    if not cleaned or cleaned in (".", ".."):
        raise ValueError("name is not usable: %r" % (name,))
    return cleaned


def _escape(text: str) -> str:
    """Escape text for embedding in the XML-ish envelope (&, <, >)."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _unescape(text: str) -> str:
    """Reverse :func:`_escape` (ampersand last, so it cannot double-decode)."""
    return text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def _canonical_json(value: Any) -> str:
    """Canonical JSON: sorted keys, no whitespace padding, non-ASCII kept."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def _digest(value: Any) -> str:
    """Stable sha256 hex digest of the canonical JSON form of ``value``."""
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TaskNotification:
    """A structured task outcome shared between agents.

    Rendered as a compact ``<task-note>`` envelope. ``usage`` is any
    JSON-serializable mapping (tokens, cost, wall time, ...) and is emitted in
    canonical JSON so the same notification always renders identically.
    """

    task_id: str
    status: str
    summary: str
    result: str = ""
    usage: Dict[str, Any] = field(default_factory=dict)
    confidence: Confidence = Confidence.MEDIUM

    def to_text(self) -> str:
        """Render the compact XML-ish envelope for this notification."""
        confidence = (
            self.confidence.value
            if isinstance(self.confidence, Confidence)
            else str(self.confidence)
        )
        return (
            '<task-note task-id="%s" status="%s" confidence="%s">'
            "<summary>%s</summary><result>%s</result><usage>%s</usage>"
            "</task-note>"
            % (
                _escape(self.task_id),
                _escape(self.status),
                _escape(confidence),
                _escape(self.summary),
                _escape(self.result),
                _escape(_canonical_json(self.usage)),
            )
        )

    @classmethod
    def from_text(cls, text: str) -> "TaskNotification":
        """Parse an envelope produced by :meth:`to_text` (tolerant).

        Raises ``ValueError`` when the required ``task-id`` or ``status``
        attributes cannot be recovered. Unknown confidence values fall back
        to ``Confidence.MEDIUM`` and malformed usage JSON falls back to ``{}``.
        """
        if not isinstance(text, str):
            raise ValueError("text must be a string")

        attributes = dict(_ATTR_RE.findall(text))
        task_id = attributes.get("task-id")
        status = attributes.get("status")
        if not task_id:
            raise ValueError("missing task-id in notification")
        if not status:
            raise ValueError("missing status in notification")

        confidence = Confidence.MEDIUM
        raw_confidence = attributes.get("confidence")
        if raw_confidence:
            try:
                confidence = Confidence(raw_confidence)
            except ValueError:
                confidence = Confidence.MEDIUM

        summary = cls._child(text, "summary")
        result = cls._child(text, "result")
        raw_usage = cls._child(text, "usage")
        usage: Dict[str, Any] = {}
        if raw_usage:
            try:
                parsed = json.loads(raw_usage)
            except ValueError:
                parsed = None
            if isinstance(parsed, dict):
                usage = parsed

        return cls(
            task_id=_unescape(task_id),
            status=_unescape(status),
            summary=summary,
            result=result,
            usage=usage,
            confidence=confidence,
        )

    @staticmethod
    def _child(text: str, tag: str) -> str:
        """Return the unescaped text of the first ``<tag> ... </tag>``."""
        pattern = re.compile(
            "<%s>(.*?)</%s>" % (re.escape(tag), re.escape(tag)), re.DOTALL
        )
        match = pattern.search(text)
        if match is None:
            return ""
        return _unescape(match.group(1))

    def to_dict(self) -> Dict[str, Any]:
        """Return the canonical dict form used for durable storage."""
        confidence = (
            self.confidence.value
            if isinstance(self.confidence, Confidence)
            else str(self.confidence)
        )
        return {
            "task_id": self.task_id,
            "status": self.status,
            "summary": self.summary,
            "result": self.result,
            "usage": dict(self.usage),
            "confidence": confidence,
        }


class SharedBoard:
    """A durable, session-isolated coordination board rooted in a directory.

    Reads are safe to run in parallel. Writes to a given file-set are
    serialized by a lock keyed on the set's ``safe_name``; appends to a topic
    are serialized under the same keyed-lock mechanism. Nothing is ever
    deleted: topics only grow and file-sets are only created or replaced with
    new content.
    """

    def __init__(self, root: str) -> None:
        if not isinstance(root, str):
            raise TypeError("root must be str")
        self.root = root
        self._lock = threading.Lock()
        self._locks: Dict[str, threading.Lock] = {}

    # -- internals ---------------------------------------------------------

    def _keyed_lock(self, key: str) -> threading.Lock:
        """Return the lock for ``key``, creating it under the master lock."""
        with self._lock:
            lock = self._locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._locks[key] = lock
            return lock

    def _ensure_root(self) -> None:
        if not os.path.isdir(self.root):
            os.makedirs(self.root, exist_ok=True)

    def _topic_path(self, topic: str) -> str:
        return os.path.join(self.root, safe_name(topic) + _JSONL_SUFFIX)

    def _file_path(self, name: str) -> str:
        return os.path.join(self.root, safe_name(name))

    @staticmethod
    def _read_lines(path: str) -> List[str]:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return handle.read().splitlines()
        except FileNotFoundError:
            return []

    # -- topics ------------------------------------------------------------

    def publish(self, topic: str, record: Dict[str, Any]) -> str:
        """Append ``record`` to ``topic`` as one JSONL line.

        Appends are idempotent by the canonical digest of ``record``: if a
        line with the same digest already exists in the topic, nothing is
        written. Returns the topic file path.
        """
        if not isinstance(record, dict):
            raise TypeError("record must be a dict")
        self._ensure_root()
        path = self._topic_path(topic)
        canonical = _canonical_json(record)
        digest = _digest(record)

        with self._keyed_lock("topic:" + os.path.basename(path)):
            for line in self._read_lines(path):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    existing = json.loads(stripped)
                except ValueError:
                    continue
                if _digest(existing) == digest:
                    return path
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(canonical + "\n")
        return path

    def read(self, topic: str, limit: int = 0) -> List[Dict[str, Any]]:
        """Return topic records in publish order; ``limit=0`` means all."""
        path = self._topic_path(topic)
        records: List[Dict[str, Any]] = []
        for line in self._read_lines(path):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                value = json.loads(stripped)
            except ValueError:
                continue
            records.append(value)
        if limit and limit > 0:
            return records[: int(limit)]
        return records

    # -- file-sets ---------------------------------------------------------

    def write_file(self, name: str, content: str) -> str:
        """Write a file-set idempotently and return its path.

        The whole write is serialized by a lock keyed on the set's safe name.
        If the file already exists with byte-identical content, it is left
        untouched (so its stat identity is preserved) and its path returned.
        """
        if not isinstance(content, str):
            raise TypeError("content must be str")
        path = self._file_path(name)

        with self._keyed_lock("file:" + os.path.basename(path)):
            self._ensure_root()
            if os.path.isfile(path):
                try:
                    with open(path, "r", encoding="utf-8") as handle:
                        if handle.read() == content:
                            return path
                except OSError:
                    pass
            temp_path = path + ".tmp-%d" % os.getpid()
            try:
                with open(temp_path, "w", encoding="utf-8", newline="") as handle:
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_path, path)
            except OSError as exc:
                try:
                    if os.path.isfile(temp_path):
                        os.remove(temp_path)
                except OSError:
                    pass
                raise WriteConflict("failed writing %r: %s" % (path, exc))
        return path

    def read_file(self, name: str) -> Optional[str]:
        """Return the content of a file-set, or ``None`` when it is absent."""
        path = self._file_path(name)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return handle.read()
        except FileNotFoundError:
            return None

    def files(self) -> List[str]:
        """Return the sorted names of the board's file-sets.

        Topic files (``*.jsonl``) are excluded; only file-sets created via
        :meth:`write_file` are reported.
        """
        if not os.path.isdir(self.root):
            return []
        names = []
        for entry in os.listdir(self.root):
            if entry.endswith(_JSONL_SUFFIX):
                continue
            if os.path.isfile(os.path.join(self.root, entry)):
                names.append(entry)
        return sorted(names)

    # -- notifications -----------------------------------------------------

    def notify(self, topic: str, notification: TaskNotification) -> str:
        """Publish ``notification`` under ``topic`` and return the path."""
        if not isinstance(notification, TaskNotification):
            raise TypeError("notification must be a TaskNotification")
        return self.publish(topic, notification.to_dict())

    def notifications(self, topic: str) -> List[TaskNotification]:
        """Parse stored topic records back into notifications.

        Records that do not carry the required ``task_id`` / ``status`` keys
        are skipped rather than raising, keeping the read tolerant.
        """
        parsed: List[TaskNotification] = []
        for record in self.read(topic):
            if not isinstance(record, dict):
                continue
            task_id = record.get("task_id")
            status = record.get("status")
            if not task_id or not status:
                continue
            confidence = Confidence.MEDIUM
            raw_confidence = record.get("confidence")
            if raw_confidence:
                try:
                    confidence = Confidence(raw_confidence)
                except ValueError:
                    confidence = Confidence.MEDIUM
            usage = record.get("usage")
            if not isinstance(usage, dict):
                usage = {}
            parsed.append(
                TaskNotification(
                    task_id=task_id,
                    status=status,
                    summary=str(record.get("summary", "")),
                    result=str(record.get("result", "")),
                    usage=usage,
                    confidence=confidence,
                )
            )
        return parsed

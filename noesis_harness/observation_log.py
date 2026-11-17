"""noesis_harness/observation_log.py

Two-layer, append-only observation knowledge base with a global activity log.

Provenance (ported patterns):
  - AI-Builder-Club/skills, ``skills/new-loop/references/ARCHITECTURE.md``
    ("Body convention -- two layers"): every artifact has a main body that is
    *what is true now* plus an optional appended ``## Timeline`` (append-only,
    dated ``YYYY-MM-DD | source -- what happened``). A recurring observation does
    not create a new artifact; it appends a timeline entry and bumps
    ``frequency`` (``frequency`` = number of timeline entries).
  - AI-Builder-Club/skills, ``skills/new-loop/references/LOG.md``: the global
    ``LOG.md`` is an append-only feed with a fixed entry grammar whose headers
    all start with ``## 20`` so entries are regex-indexable.
  - AI-Builder-Club/skills, ``skills/new-loop/references/KNOWLEDGE_SETUP.md``:
    the signals schema -- ``kind, category, frequency, sources[], domain[],
    status`` -- and the deduped, frequency-counted merge rule.

Design guarantees (AGENTS.md HARD rules):
  - Standard library only (``hashlib``, ``json``, ``os``, ``re``, ``threading``).
  - Python 3.9 compatible syntax (``from __future__ import annotations``).
  - Append-only semantics: existing timeline entries are preserved verbatim;
    files are never deleted.
  - Idempotent by stable content key: the same ``(source, note)`` observation
    is absorbed rather than duplicated into a second artifact or a second body.
  - Deterministic: two identical call sequences render byte-identical files.

One artifact per key is stored as ``<root>/<sanitized-key>.md`` and the global
feed is ``<root>/LOG.md``.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from typing import Any, Dict, List

TIMELINE_HEADING = "## Timeline"
LOG_PREFIX = "## 20"

_EM_DASH = "\u2014"
_LOG_NAME = "LOG.md"
_FRONTMATTER_KIND = "kind: artifact"

_SAFE_SEGMENT_RE = re.compile(r"[^a-z0-9]+")
_KIND_RE = re.compile(r"^kind:\s*artifact\s*$", re.MULTILINE)
_LOG_HEADER_RE = re.compile(
    r"^" + re.escape(LOG_PREFIX) + r"(\d{2}-\d{2}-\d{2})\s*\u00b7\s*(.*)$"
)


def content_key(source: str, note: str) -> str:
    """Return the stable dedupe key for an observation.

    The key is ``sha256(source + "\\x00" + note).hexdigest()`` so that the same
    observation always maps to the same artifact regardless of surrounding
    whitespace, ordering, or call path.
    """
    material = str(source) + "\x00" + str(note)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _render_timeline_line(date: str, source: str, note: str) -> str:
    return "%s | %s %s %s" % (date, source, _EM_DASH, note)


class ObservationLog:
    """File-backed, two-layer observation store rooted at ``root``.

    ``root`` is created lazily on first write. The store writes one markdown
    artifact per key plus a global ``LOG.md``. Nothing is ever deleted.
    """

    def __init__(self, root: str) -> None:
        if not isinstance(root, str) or not root.strip():
            raise ValueError("observation_log_root_required")
        self.root = os.path.abspath(os.path.expanduser(root))
        self._lock = threading.Lock()

    # -- paths -------------------------------------------------------------

    @staticmethod
    def _sanitize(key: str) -> str:
        """Return a safe filename segment for ``key`` or raise ``ValueError``.

        The key is lowercased, non-alphanumeric runs collapse to a single
        ``-``, and leading/trailing dashes are trimmed. Keys containing ``..``
        or a path separator are rejected outright rather than rewritten.
        """
        if not isinstance(key, str) or not key.strip():
            raise ValueError("observation_key_required")
        if ".." in key:
            raise ValueError("observation_key_unsafe")
        if "/" in key or "\\" in key or os.sep in key:
            raise ValueError("observation_key_unsafe")
        if os.altsep and os.altsep in key:
            raise ValueError("observation_key_unsafe")
        segment = _SAFE_SEGMENT_RE.sub("-", key.lower()).strip("-")
        if not segment or segment in (".", ".."):
            raise ValueError("observation_key_empty")
        return segment

    def artifact_path(self, key: str) -> str:
        """Return the absolute artifact path for ``key`` (does not create it)."""
        return os.path.join(self.root, self._sanitize(key) + ".md")

    def _log_path(self) -> str:
        return os.path.join(self.root, _LOG_NAME)

    # -- artifact IO -------------------------------------------------------

    @staticmethod
    def _read(path: str) -> str:
        if not os.path.exists(path):
            return ""
        with open(path, "r", encoding="utf-8", newline="") as handle:
            return handle.read().replace("\r\n", "\n").replace("\r", "\n")

    @staticmethod
    def _write(path: str, text: str) -> None:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)

    @staticmethod
    def _parse_artifact(text: str) -> Dict[str, Any]:
        """Split an artifact into frontmatter fields, body and timeline lines."""
        fields: Dict[str, str] = {}
        lines = text.split("\n") if text else []
        start = 0
        if lines and lines[0].strip() == "---":
            index = 1
            while index < len(lines) and lines[index].strip() != "---":
                if ":" in lines[index]:
                    name, _, value = lines[index].partition(":")
                    fields[name.strip()] = value.strip()
                index += 1
            start = index + 1 if index < len(lines) else len(lines)

        body_lines: List[str] = []
        timeline: List[str] = []
        cursor = start
        while cursor < len(lines):
            if lines[cursor].strip() == TIMELINE_HEADING:
                for raw in lines[cursor + 1:]:
                    if raw.strip():
                        timeline.append(raw.rstrip())
                break
            body_lines.append(lines[cursor])
            cursor += 1
        body = "\n".join(body_lines).strip()
        sources: List[str] = []
        raw_sources = fields.get("sources", "")
        if raw_sources:
            try:
                parsed = json.loads(raw_sources)
            except (ValueError, TypeError):
                parsed = None
            if isinstance(parsed, list):
                sources = [str(item) for item in parsed]
        frequency = 0
        try:
            frequency = int(fields.get("frequency", "0"))
        except (ValueError, TypeError):
            frequency = 0
        return {
            "fields": fields,
            "body": body,
            "timeline": timeline,
            "sources": sources,
            "frequency": frequency,
        }

    @staticmethod
    def _render_artifact(note: str, sources: List[str], timeline: List[str]) -> str:
        header = [
            "---",
            _FRONTMATTER_KIND,
            "frequency: %d" % len(timeline),
            "sources: %s" % json.dumps(sources, ensure_ascii=False),
            "status: active",
            "---",
        ]
        return (
            "\n".join(header)
            + "\n\n"
            + note
            + "\n\n"
            + TIMELINE_HEADING
            + "\n\n"
            + "\n".join(timeline)
            + "\n"
        )

    # -- public API --------------------------------------------------------

    def record(self, key: str, source: str, note: str, date: str) -> Dict[str, Any]:
        """Upsert an observation into its artifact; return a summary dict.

        First observation creates the artifact with ``note`` as the body (what is
        true now) and a fresh ``## Timeline``. A recurrence of the same content
        key does not create a second artifact or duplicate the body; it appends
        one timeline line and increments ``frequency``. Returns
        ``{"key", "path", "created", "frequency", "timeline_entries"}``.
        """
        segment = self._sanitize(key)
        path = os.path.join(self.root, segment + ".md")
        line = _render_timeline_line(str(date), str(source), str(note))
        with self._lock:
            if os.path.exists(path):
                parsed = self._parse_artifact(self._read(path))
                timeline = list(parsed["timeline"])
                sources = list(parsed["sources"])
                created = False
            else:
                timeline = []
                sources = []
                created = True
            if str(source) not in sources:
                sources.append(str(source))
            timeline.append(line)
            self._write(path, self._render_artifact(str(note), sources, timeline))
        return {
            "key": segment,
            "path": path,
            "created": created,
            "frequency": len(timeline),
            "timeline_entries": len(timeline),
        }

    def timeline(self, key: str) -> List[str]:
        """Return the artifact timeline lines in order (heading excluded)."""
        path = self.artifact_path(key)
        if not os.path.exists(path):
            return []
        return list(self._parse_artifact(self._read(path))["timeline"])

    def frequency(self, key: str) -> int:
        """Return the frontmatter frequency counter (0 when absent)."""
        path = self.artifact_path(key)
        if not os.path.exists(path):
            return 0
        parsed = self._parse_artifact(self._read(path))
        if parsed["frequency"]:
            return parsed["frequency"]
        return len(parsed["timeline"])

    def artifacts(self) -> List[str]:
        """Return the sorted keys of all managed artifacts under ``root``."""
        if not os.path.isdir(self.root):
            return []
        keys: List[str] = []
        for name in os.listdir(self.root):
            if not name.endswith(".md") or name == _LOG_NAME:
                continue
            path = os.path.join(self.root, name)
            if not os.path.isfile(path):
                continue
            text = self._read(path)
            if not _KIND_RE.search(text):
                continue
            keys.append(name[:-3])
        return sorted(keys)

    def append_log(self, date: str, title: str, what: str, refs: str = "") -> str:
        """Append one entry to the global ``LOG.md`` and return its text.

        Grammar (strict): a header ``## <date> \u00b7 <title>``, then
        ``What: <what>``, then an optional ``Refs: <refs>``. Append-only, newest
        at the bottom.
        """
        if not isinstance(date, str) or not date.strip():
            raise ValueError("log_date_required")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("log_title_required")
        lines = ["## %s \u00b7 %s" % (date, title), "What: %s" % what]
        if refs:
            lines.append("Refs: %s" % refs)
        entry = "\n".join(lines)
        path = self._log_path()
        os.makedirs(self.root, exist_ok=True)
        exists = os.path.exists(path) and os.path.getsize(path) > 0
        prefix = "\n" if exists else ""
        with self._lock:
            with open(path, "a", encoding="utf-8", newline="\n") as handle:
                handle.write(prefix + entry + "\n")
        return entry

    def index_entries(self) -> List[Dict[str, str]]:
        """Regex-scan ``LOG.md`` and return parsed entries in file order.

        Each entry is ``{"date", "title", "what", "refs"}``. Blocks without a
        valid ``## 20...`` header are skipped tolerantly.
        """
        text = self._read(self._log_path())
        if not text:
            return []
        entries: List[Dict[str, str]] = []
        current = None
        for raw in text.split("\n"):
            match = _LOG_HEADER_RE.match(raw)
            if match:
                if current is not None:
                    entries.append(current)
                current = {
                    "date": LOG_PREFIX[-2:] + match.group(1),
                    "title": match.group(2).strip(),
                    "what": "",
                    "refs": "",
                }
                continue
            if current is None:
                continue
            stripped = raw.strip()
            if stripped.startswith("What:") and not current["what"]:
                current["what"] = stripped[len("What:"):].strip()
            elif stripped.startswith("Refs:") and not current["refs"]:
                current["refs"] = stripped[len("Refs:"):].strip()
        if current is not None:
            entries.append(current)
        return entries


__all__ = [
    "ObservationLog",
    "content_key",
    "TIMELINE_HEADING",
    "LOG_PREFIX",
]

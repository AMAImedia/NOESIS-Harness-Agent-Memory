"""noesis_harness/domain_library.py

Per-domain libraries of adopted artifacts: what earlier tasks in THIS area of
work produced, and why each one was adopted.

Patterns borrowed from:
- Harness2 (Google, Apache-2.0, arXiv 2610.14224) ``core/library.py`` --
  the ``<root>/<run-tag>/<domain>/INDEX.md`` layout, the "the whole tree is
  carried, never a summary" rule, and retrieval *by construction*: a domain's
  directory only ever holds same-domain entries, so cross-area leakage needs
  no filter because there is no path by which it could occur.
- Harness2 ``EXPERIENCE.md`` -- the three-part lesson record (why it was
  chosen / what each edit did / the transferable lesson) plus a one-line cue
  in the index, so a reader browses the index first and opens only what looks
  relevant.

Clean-room: no Harness2 code was copied; only the layout idea was ported.

What is deliberately different from Harness2, and why:

- Harness2 writes straight into the library from its reflection step. NOESIS
  does not: an entry lands here only through :meth:`DomainLibrary.add`, which
  requires a named approver, and a lesson becomes recallable only after
  ``lesson_cue.LessonJournal.promote``. Nothing here auto-promotes.
- Nothing is ever deleted from the journal, but the on-disk view can be
  narrowed to a *prefix* of the task stream (:meth:`retain`), so a measured
  run can be held to only the entries that existed before it. That is their
  ``retain`` rule and it is what keeps a benchmark honest.
- Stdlib only; no LLM anywhere in this module.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from .lesson_cue import (
        Lesson,
        LessonCueError,
        LessonJournal,
        canonical,
        normalize_domain,
    )
except ImportError:  # pragma: no cover - direct script import
    from noesis_harness.lesson_cue import (
        Lesson,
        LessonCueError,
        LessonJournal,
        canonical,
        normalize_domain,
    )


SCHEMA_VERSION = "noesis.domain-library.v1"

INDEX_NAME = "INDEX.md"
ENTRIES_DIR = "entries"
EXPERIENCE_NAME = "EXPERIENCE.md"

_SEP_RE = re.compile(r"\s*[/\\]\s*")
_UNSAFE_RE = re.compile(r"[^A-Za-z0-9._\-]")


class DomainLibraryError(ValueError):
    """Raised when an entry or a library path is malformed."""


def _no_traversal(name: str) -> str:
    """Make a path component incapable of climbing out of its parent.

    A separator is the obvious escape and is collapsed first, but a component
    that is *itself* ``..`` needs no separator at all -- ``root / ".."`` is the
    parent directory. So a component made only of dots is escaped too, and
    every other unsafe character is percent-encoded rather than dropped, so two
    different labels can never collapse onto one folder.
    """
    if not name:
        return "unknown"
    if set(name) == {"."}:
        return "".join("%2E" for _ in name)
    return _UNSAFE_RE.sub(lambda m: "%%%02X" % ord(m.group(0)), name)


def slug(value: str) -> str:
    """A filesystem-safe, reversible-enough name for a task id.

    Separators become double underscores. Anything else that the filesystem
    cannot hold is percent-escaped rather than dropped, so two different task
    ids can never collapse onto one entry directory.
    """
    text = str(value or "")
    if not text.strip():
        raise DomainLibraryError("task_id_required")
    return _no_traversal(_SEP_RE.sub("__", text).strip())


def domain_dir(domain: str) -> str:
    """One directory name for a domain, never a path.

    Only separators and the whitespace around them collapse, so a domain
    without one maps to itself. ``../`` becomes ``__..``, which stays inside
    the library root, and a label that is itself ``..`` is escaped: a domain
    label can never walk out of its own folder.
    """
    normalized = normalize_domain(domain)
    return _no_traversal(_SEP_RE.sub("__", normalized)) or "unknown"


@dataclass(frozen=True)
class LibraryEntry:
    """One adopted artifact from one earlier task in one domain.

    ``artifacts`` carries the files themselves -- the full tree, not a summary
    of it. ``why`` is why this was adopted over what was tried. ``lesson`` is
    the transferable part, stored as a :class:`~noesis_harness.lesson_cue.Lesson`
    so the same record can be recalled later by cue.
    """

    task_id: str
    domain: str
    cue: str
    why: str = ""
    artifacts: Tuple[Tuple[str, str], ...] = ()
    lesson: Optional[Lesson] = None
    label: str = ""
    source_ids: Tuple[str, ...] = ()
    created_at: float = 0.0
    approved_by: str = ""
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not str(self.task_id).strip():
            raise DomainLibraryError("task_id_required")
        if not str(self.domain).strip():
            raise DomainLibraryError("domain_required")
        if not str(self.cue).strip():
            raise DomainLibraryError("cue_required")
        if not str(self.approved_by).strip():
            raise DomainLibraryError("approved_by_required")
        if self.lesson is not None:
            if normalize_domain(self.lesson.domain) != normalize_domain(self.domain):
                raise DomainLibraryError("lesson_domain_must_match_entry_domain")
            if not str(self.lesson.evidence).strip():
                raise DomainLibraryError("lesson_evidence_required")
        for rel, body in self.artifacts:
            _check_relative(rel)
            if not isinstance(body, str):
                raise DomainLibraryError("artifact_body_must_be_text")

    @property
    def content_digest(self) -> str:
        """Digest over what the entry means and holds.

        Two entries for the same task with the same artifacts and the same cue
        are the same entry, which is what makes ``add`` idempotent.
        """
        body = canonical(
            {
                "domain": normalize_domain(self.domain),
                "cue": self.cue.strip().casefold(),
                "why": self.why.strip().casefold(),
                "artifacts": [[rel, hashlib.sha256(body.encode("utf-8")).hexdigest()] for rel, body in self.artifacts],
                "lesson": self.lesson.fingerprint if self.lesson else "",
            }
        )
        return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()

    def inventory(self) -> Dict[str, Any]:
        """A one-line census of what this entry actually carries."""
        names = [rel for rel, _ in self.artifacts]
        chars = sum(len(body) for _, body in self.artifacts)
        return {
            "files": len(names),
            "chars": chars,
            "kinds": sorted({rel.split("/", 1)[0] for rel in names}) or ["lesson_only"],
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "domain": self.domain,
            "cue": self.cue,
            "why": self.why,
            "label": self.label,
            "artifacts": [[rel, body] for rel, body in self.artifacts],
            "lesson": self.lesson.to_dict() if self.lesson else None,
            "source_ids": list(self.source_ids),
            "created_at": self.created_at,
            "approved_by": self.approved_by,
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LibraryEntry":
        lesson_payload = data.get("lesson")
        return cls(
            task_id=str(data.get("task_id") or ""),
            domain=str(data.get("domain") or ""),
            cue=str(data.get("cue") or ""),
            why=str(data.get("why") or ""),
            artifacts=tuple((str(rel), str(body)) for rel, body in (data.get("artifacts") or ())),
            lesson=Lesson.from_dict(lesson_payload) if isinstance(lesson_payload, dict) else None,
            label=str(data.get("label") or ""),
            source_ids=tuple(data.get("source_ids") or ()),
            created_at=float(data.get("created_at") or 0.0),
            approved_by=str(data.get("approved_by") or ""),
            schema_version=str(data.get("schema_version") or SCHEMA_VERSION),
        )


@dataclass
class LibraryReport:
    """What one ``add``/``forget``/``retain`` operation did."""

    action: str
    domain: str
    changed: bool
    entry: str = ""
    reason: str = ""
    detail: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "action": self.action,
            "domain": self.domain,
            "changed": self.changed,
            "entry": self.entry,
            "reason": self.reason,
            "detail": self.detail,
        }


def _check_relative(rel: str) -> None:
    """Reject artifact paths that escape the entry directory.

    The check is on the path text, before any join: an artifact called
    ``../../other-domain/answer.txt`` is refused, not normalised.
    """
    text = str(rel).replace("\\", "/").strip()
    if not text:
        raise DomainLibraryError("artifact_path_required")
    if text.startswith("/") or ".." in text.split("/") or text.startswith("~"):
        raise DomainLibraryError("artifact_path_escapes: %r" % rel)


class DomainLibrary:
    """One (root, domain) library: appended to after a task, read before the next."""

    def __init__(
        self,
        root: str,
        domain: str,
        *,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        self.root = Path(root)
        self.domain = str(domain or "").strip()
        if not self.domain:
            raise DomainLibraryError("domain_required")
        self.clock = clock or time.time

    # -- layout ------------------------------------------------------------

    @property
    def dir(self) -> Path:
        return self.root / domain_dir(self.domain)

    @property
    def index(self) -> Path:
        return self.dir / INDEX_NAME

    @property
    def entries_dir(self) -> Path:
        return self.dir / ENTRIES_DIR

    def entry_dir(self, task_id: str) -> Path:
        return self.entries_dir / slug(task_id)

    def exists(self) -> bool:
        return self.index.is_file()

    def context_dir(self) -> Optional[Path]:
        """The folder to hand to a reader, or ``None`` when this domain is empty.

        Returning ``None`` rather than an empty folder keeps a caller from
        pointing a prompt at a library that holds nothing.
        """
        if not self.exists():
            return None
        return self.dir if any(self.entries_dir.glob("*/" + EXPERIENCE_NAME)) else None

    # -- reading -----------------------------------------------------------

    def task_ids(self) -> List[str]:
        """Entry task ids in stream order.

        Order is the write order, carried in each entry's ``seq``, so a
        replayed library reads exactly as it was accumulated -- which is what
        makes ``retain`` a prefix rather than an arbitrary subset.
        """
        return [str(payload.get("task_id") or "") for payload in self._ordered_payloads()]

    def read(self, task_id: str) -> Optional[LibraryEntry]:
        payload = self._read_json(self.entry_dir(task_id) / "entry.json")
        return LibraryEntry.from_dict(payload) if payload else None

    def entries(self) -> List[LibraryEntry]:
        """Every entry, in stream order. Unknown tasks are skipped, not fatal.

        Ordered by ``seq``, not by ``created_at``: the two views of a library
        must never disagree about which entry came first.
        """
        out: List[LibraryEntry] = []
        for payload in self._ordered_payloads():
            try:
                out.append(LibraryEntry.from_dict(payload))
            except DomainLibraryError:
                continue
        return out

    def cues(self) -> List[str]:
        """The one-line cue of every entry, for index browsing."""
        return [entry.cue for entry in self.entries()]

    # -- writing -----------------------------------------------------------

    def add(self, entry: LibraryEntry, *, seq: Optional[int] = None) -> LibraryReport:
        """Store one adopted artifact, idempotently.

        Re-adding byte-identical content is a no-op. Re-adding the same task
        with different content overwrites that task's *entry folder* only --
        which is why :meth:`forget` exists and why the journal in
        ``lesson_cue`` stays the durable record. Returns a report; never
        raises for the ordinary cases.
        """
        if normalize_domain(entry.domain) != normalize_domain(self.domain):
            return LibraryReport(
                action="add",
                domain=self.domain,
                changed=False,
                entry=entry.task_id,
                reason="domain_mismatch",
            )
        existing = self.read(entry.task_id)
        if existing is not None and existing.content_digest == entry.content_digest:
            return LibraryReport(
                action="add",
                domain=self.domain,
                changed=False,
                entry=entry.task_id,
                reason="already_present",
                detail={"content_digest": entry.content_digest},
            )

        target = self.entry_dir(entry.task_id)
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        target.mkdir(parents=True, exist_ok=True)

        stamp = float(entry.created_at) if entry.created_at else float(self.clock())
        position = seq if seq is not None else len(self.task_ids())
        payload = dict(entry.to_dict())
        payload["seq"] = position
        payload["created_at"] = stamp
        self._write(target / "entry.json", payload)

        for rel, body in entry.artifacts:
            path = target / "artifacts" / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")

        (target / EXPERIENCE_NAME).write_text(self._experience_md(entry, stamp), encoding="utf-8")
        self.rebuild_index()
        return LibraryReport(
            action="add",
            domain=self.domain,
            changed=True,
            entry=entry.task_id,
            reason="stored",
            detail={"content_digest": entry.content_digest, "seq": position, "inventory": entry.inventory()},
        )

    def forget(self, task_ids: Iterable[str]) -> List[LibraryReport]:
        """Drop entries for these tasks and rebuild the index.

        Used to hold a measured run to a known prefix. Unknown ids are ignored
        rather than fatal, so a caller can pass a superset safely.
        """
        reports: List[LibraryReport] = []
        for task_id in task_ids:
            path = self.entry_dir(task_id)
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
                reports.append(
                    LibraryReport("forget", self.domain, True, entry=task_id, reason="dropped")
                )
            else:
                reports.append(
                    LibraryReport("forget", self.domain, False, entry=task_id, reason="absent")
                )
        if any(report.changed for report in reports):
            self.rebuild_index()
        return reports

    def retain(self, task_ids: Sequence[str]) -> List[LibraryReport]:
        """Keep only the entries preceding the current task in this stream."""
        keep = {slug(task_id) for task_id in task_ids}
        dropped = [t for t in self.task_ids() if slug(t) not in keep]
        return self.forget(dropped)

    # -- index -------------------------------------------------------------

    def rebuild_index(self) -> Path:
        """Regenerate ``INDEX.md`` from what is actually on disk.

        The index is a navigation aid, never a source of truth: it is rebuilt
        from the entries, so a stale or truncated index cannot mislead.
        """
        rows = [
            "# Library -- %s" % self.domain,
            "",
            "Each entry is an earlier task in THIS domain whose artifact was adopted, "
            "stored with its full content and why it was picked. Browse this index, "
            "then open the entries that look relevant to the matter in front of you.",
            "",
        ]
        task_ids = self.task_ids()
        if not task_ids:
            rows.append("_(empty -- this is the first task in this domain)_")
        for task_id in task_ids:
            entry = self.read(task_id)
            if entry is None:
                continue
            folder = "entries/" + slug(task_id)
            rows.append("## `%s/`" % folder)
            rows.append(
                "- content: `%s/artifacts/` -- %d file(s), %s char(s)"
                % (folder, entry.inventory()["files"], entry.inventory()["chars"])
            )
            rows.append("- why:     `%s/%s`" % (folder, EXPERIENCE_NAME))
            rows.append("- cue:     %s" % entry.cue.strip())
            if entry.lesson is not None:
                rows.append("- lesson:  %s" % entry.lesson.lesson.strip())
            rows.append("")
        self.dir.mkdir(parents=True, exist_ok=True)
        self.index.write_text("\n".join(rows), encoding="utf-8")
        return self.index

    # -- internals ---------------------------------------------------------

    def _entry_files(self) -> List[Path]:
        if not self.entries_dir.is_dir():
            return []
        return sorted(self.entries_dir.glob("*/entry.json"))

    def _ordered_payloads(self) -> List[Dict[str, Any]]:
        """Every entry payload, in one agreed order: ``seq`` then ``task_id``.

        There is exactly one ordering here on purpose. ``task_ids``,
        ``entries`` and ``retain`` must all agree, or a prefix computed by one
        and a list printed by another would silently disagree about which
        entries existed before a given task.
        """
        rows: List[Tuple[int, str, Dict[str, Any]]] = []
        for path in self._entry_files():
            payload = self._read_json(path)
            if payload:
                rows.append((int(payload.get("seq") or 0), str(payload.get("task_id") or ""), payload))
        rows.sort(key=lambda row: (row[0], row[1]))
        return [row[2] for row in rows]

    @staticmethod
    def _read_json(path: Path) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    @staticmethod
    def _write(path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".%d.tmp" % os.getpid())
        tmp.write_text(canonical(payload), encoding="utf-8")
        os.replace(tmp, path)

    @staticmethod
    def _experience_md(entry: LibraryEntry, stamp: float) -> str:
        lines = [
            "# %s" % entry.task_id,
            "",
            "- domain: `%s`" % entry.domain,
            "- adopted: `%s`" % (entry.label or "unnamed"),
            "- approved by: `%s`" % entry.approved_by,
            "- recorded at: %.3f" % stamp,
            "- content: %s" % canonical(entry.inventory()),
            "",
        ]
        if entry.why.strip():
            lines += ["## Why this was chosen", entry.why.strip(), ""]
        if entry.lesson is not None:
            lines += [
                "## Transferable lesson",
                "- **cue**: %s" % entry.lesson.cue,
                "- **lesson**: %s" % entry.lesson.lesson,
                "- **evidence**: %s" % entry.lesson.evidence,
                "- **confidence**: %s" % entry.lesson.confidence,
                "",
            ]
        if entry.source_ids:
            lines += ["## Sources", ", ".join(entry.source_ids), ""]
        return "\n".join(lines)


class DomainLibraryRoot:
    """The set of per-domain libraries under one root.

    Each domain is physically separate, so a caller that only ever opens the
    domain it needs cannot see another's entries. This object exists for
    bookkeeping -- listing domains, reporting totals -- not for searching
    across them.
    """

    def __init__(self, root: str, *, clock: Optional[Callable[[], float]] = None) -> None:
        self.root = Path(root)
        self.clock = clock or time.time

    def library(self, domain: str) -> DomainLibrary:
        return DomainLibrary(str(self.root), domain, clock=self.clock)

    def domains(self) -> List[str]:
        """Domain directory names present on disk, sorted."""
        if not self.root.is_dir():
            return []
        return sorted(p.name for p in self.root.iterdir() if p.is_dir())

    def total_entries(self) -> int:
        return sum(len(self.library(name).task_ids()) for name in self.domains())

    def report(self) -> Dict[str, Any]:
        per_domain = {}
        for name in self.domains():
            library = self.library(name)
            per_domain[name] = {
                "entries": len(library.task_ids()),
                "cues": library.cues(),
                "index": str(library.index),
            }
        return {
            "schema_version": SCHEMA_VERSION,
            "root": str(self.root),
            "domains": sorted(per_domain),
            "total_entries": self.total_entries(),
            "per_domain": per_domain,
        }


def publish_lesson(
    journal: LessonJournal,
    entry: LibraryEntry,
    *,
    actor: str,
    reason: str = "",
) -> Optional[str]:
    """Send an entry's lesson into the cue-recall journal, if it has one.

    This is the seam between the two halves of NOESIS. A ``LibraryEntry`` may
    carry a lesson; until it is published, nothing can recall it by cue. The
    lesson is appended as a CANDIDATE -- :func:`publish_lesson` does not
    promote it, and an operator still has to say so.
    """
    if entry.lesson is None:
        return None
    try:
        return journal.record(
            entry.lesson,
            "record",
            actor=str(actor or ""),
            reason=reason or ("from domain library entry %s" % entry.task_id),
        )
    except LessonCueError as exc:
        raise DomainLibraryError(str(exc))


__all__ = [
    "DomainLibrary",
    "DomainLibraryError",
    "DomainLibraryRoot",
    "LibraryEntry",
    "LibraryReport",
    "SCHEMA_VERSION",
    "domain_dir",
    "publish_lesson",
    "slug",
]
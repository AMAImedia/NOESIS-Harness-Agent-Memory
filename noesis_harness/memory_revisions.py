"""noesis_harness/memory_revisions.py

Stdlib-only append-only memory revision log with compare-and-swap (CAS) replace,
history/restore, and cross-scope provenance mirroring.

Borrowed patterns:
  - qm (yc-software/qm), src/memory/postgres-memory-service.ts: a per-scope
    revision log where every mutation is an append and writes are guarded by a
    compare-and-swap on the last observed revision (replaceIfRevision). A stale
    writer raises a conflict instead of silently clobbering a newer head.
  - qm (yc-software/qm), src/memory/memory-service.ts: provenance mirroring.
    A fact recalled from another scope keeps its origin, rendered as
    "(said in <scope>)" on a mirror, while unverified text is prefixed with
    "[claimed source] " so downstream readers can tell trusted from claimed.

The log is append-only: state is a replay projection over the revision history,
never an in-place edit. The core is deterministic (the wall clock is always
injected by the caller) and never calls an LLM. An optional JSONL path gives
crash-safe persistence: every append is flushed as one line and replayed on
construction, with malformed trailing lines tolerated on read.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import List, Optional, Tuple


SCHEMA_VERSION = 1

TRUSTED_MARKERS = ("[claimed source]", "[trusted source]")

_VALID_OPS = ("add", "update", "delete")


class RevisionConflict(RuntimeError):
    """Raised when a CAS write or restore targets a stale/unknown revision."""


@dataclass(frozen=True)
class Revision:
    """A single immutable entry in the append-only revision log."""

    scope: str
    seq: int
    op: str
    body: str
    author: str
    at: float
    provenance: str = ""


class MemoryRevisions:
    """Append-only revision log for scoped memory bodies.

    Revisions are numbered by a global monotonic ``seq``. The head revision of a
    scope is the seq of its most recent entry (0 when the scope is unknown), so a
    caller can read a head and later perform a CAS write against it. An optional
    ``path`` turns the log into a JSONL file that is replayed on construction.
    """

    def __init__(self, path: Optional[str] = None) -> None:
        self._path = path
        self._log: List[Revision] = []
        self._seq = 0
        if path is not None:
            for rev in read_revision_log(path):
                self._log.append(rev)
                if rev.seq > self._seq:
                    self._seq = rev.seq

    # -- internal -----------------------------------------------------------

    def _append(self, scope: str, op: str, body: str, author: str, at: float, provenance: str) -> int:
        self._seq += 1
        rev = Revision(
            scope=scope,
            seq=self._seq,
            op=op,
            body=body,
            author=author,
            at=at,
            provenance=provenance,
        )
        self._log.append(rev)
        self._persist(rev)
        return self._seq

    def _persist(self, rev: Revision) -> None:
        if self._path is None:
            return
        parent = os.path.dirname(os.path.abspath(self._path))
        if parent and not os.path.isdir(parent):
            os.makedirs(parent, exist_ok=True)
        line = json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "scope": rev.scope,
                "seq": rev.seq,
                "op": rev.op,
                "body": rev.body,
                "author": rev.author,
                "at": rev.at,
                "provenance": rev.provenance,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        with open(self._path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    # -- reads --------------------------------------------------------------

    def read_head(self, scope: str) -> Tuple[str, int]:
        """Return ``(body, revision)`` for a scope.

        Unknown scopes yield ``("", 0)``. A deleted scope keeps its revision but
        reports an empty body, so a CAS against the delete revision still works.
        """
        for rev in reversed(self._log):
            if rev.scope == scope:
                return (rev.body, rev.seq)
        return ("", 0)

    def history(self, scope: str, limit: int = 0) -> List[Revision]:
        """Return this scope's revisions in chronological (log) order.

        ``limit`` of 0 returns the whole history; a positive limit returns the
        most recent ``limit`` entries, still in chronological order.
        """
        revs = [rev for rev in self._log if rev.scope == scope]
        if limit and limit > 0:
            revs = revs[-limit:]
        return list(revs)

    def scopes(self) -> List[str]:
        """Return every known scope, sorted and de-duplicated."""
        return sorted({rev.scope for rev in self._log})

    # -- writes -------------------------------------------------------------

    def replace_if_revision(
        self,
        scope: str,
        body: str,
        expected_revision: int,
        author: str,
        at: float,
        provenance: str = "",
    ) -> int:
        """CAS-replace a scope's body, raising if the head has moved.

        The write succeeds only when ``read_head(scope)[1] == expected_revision``;
        otherwise :class:`RevisionConflict` is raised and nothing is appended.
        """
        current = self.read_head(scope)[1]
        if current != expected_revision:
            raise RevisionConflict(
                "revision conflict for scope {0!r}: expected {1}, found {2}".format(
                    scope, expected_revision, current
                )
            )
        return self._append(scope, "update", body, author, at, provenance)

    def add(
        self,
        scope: str,
        body: str,
        author: str,
        at: float,
        provenance: str = "",
    ) -> int:
        """Append an ``add`` revision and return its new revision number.

        Unlike :meth:`replace_if_revision` this is unconditional: it is allowed
        even when the scope already has content, so callers that want
        first-writer-wins semantics must use the CAS path instead. The intent is
        to record the arrival of a fact in the log without pretending the prior
        head never existed.
        """
        return self._append(scope, "add", body, author, at, provenance)

    def delete(
        self,
        scope: str,
        expected_revision: int,
        author: str,
        at: float,
    ) -> int:
        """CAS-delete a scope: its head body becomes ``""`` and a delete entry
        is appended. Raises :class:`RevisionConflict` on a stale revision."""
        current = self.read_head(scope)[1]
        if current != expected_revision:
            raise RevisionConflict(
                "revision conflict for scope {0!r}: expected {1}, found {2}".format(
                    scope, expected_revision, current
                )
            )
        return self._append(scope, "delete", "", author, at, "")

    def restore(self, scope: str, revision: int, author: str, at: float) -> int:
        """Re-apply a historical body by appending a new ``update``.

        ``revision`` must be the seq of an entry already present in this scope's
        history; an unknown revision raises :class:`RevisionConflict`. Restoring
        never rewrites the log, it appends the old body as the new head.
        """
        target: Optional[Revision] = None
        for rev in self._log:
            if rev.scope == scope and rev.seq == revision:
                target = rev
                break
        if target is None:
            raise RevisionConflict(
                "unknown revision {0} for scope {1!r}".format(revision, scope)
            )
        return self._append(
            scope,
            "update",
            target.body,
            author,
            at,
            "restored from revision {0}".format(revision),
        )

    def mirror(self, from_scope: str, to_scope: str, author: str, at: float) -> int:
        """Copy the head body of ``from_scope`` into ``to_scope``.

        The mirrored entry is tagged with provenance ``"(said in <from_scope>)"``
        so the destination scope records where the claim originated. Returns the
        new revision in ``to_scope``.
        """
        body = self.read_head(from_scope)[0]
        provenance = "(said in {0})".format(from_scope)
        return self._append(to_scope, "update", body, author, at, provenance)


def mark_untrusted(body: str) -> str:
    """Tag unverified text with a ``"[claimed source] "`` prefix.

    If ``body`` already starts with one of :data:`TRUSTED_MARKERS` it is returned
    unchanged, which makes the helper idempotent: applying it twice never stacks
    prefixes. Downstream readers can therefore treat a leading marker as the
    authoritative signal that provenance was considered.
    """
    for marker in TRUSTED_MARKERS:
        if body.startswith(marker):
            return body
    return "[claimed source] " + body


def read_revision_log(path: str) -> List[Revision]:
    """Read a JSONL revision log, tolerating a malformed tail.

    Blank lines are skipped. A line that is not valid JSON, is not an object, or
    is missing the fields a :class:`Revision` needs is ignored so that a partial
    append at crash time cannot make the whole log unreadable. Entries are
    returned in file order.
    """
    revisions: List[Revision] = []
    if not os.path.exists(path):
        return revisions
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except ValueError:
                continue
            if not isinstance(payload, dict):
                continue
            try:
                scope = payload["scope"]
                seq = payload["seq"]
                op = payload["op"]
                body = payload["body"]
                author = payload["author"]
                at = payload["at"]
            except (KeyError, TypeError):
                continue
            if not isinstance(scope, str) or not isinstance(op, str):
                continue
            if op not in _VALID_OPS:
                continue
            if not isinstance(seq, int) or isinstance(seq, bool):
                continue
            if not isinstance(at, (int, float)) or isinstance(at, bool):
                continue
            if not isinstance(body, str) or not isinstance(author, str):
                continue
            provenance = payload.get("provenance", "")
            if not isinstance(provenance, str):
                provenance = ""
            revisions.append(
                Revision(
                    scope=scope,
                    seq=seq,
                    op=op,
                    body=body,
                    author=author,
                    at=float(at),
                    provenance=provenance,
                )
            )
    return revisions


__all__ = [
    "SCHEMA_VERSION",
    "RevisionConflict",
    "Revision",
    "MemoryRevisions",
    "mark_untrusted",
    "read_revision_log",
]

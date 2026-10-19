"""noesis_harness/forget.py

Erasure that can be proven: erase by predicate, leave a tombstone, and report
what is still extractable afterwards.

Patterns borrowed from:

- **Bemula** (arXiv 2610.18052) -- the first memory-unlearning benchmark. Its
  headline result is negative: across six systems and three backbones, no
  system passes more than 1.5% of forget requests end to end. The stated cause
  is redundancy: the same information lives in several derived forms (raw
  turns, extracted facts, compressed notes), so deleting one copy leaves the
  rest. Hence :class:`Coverage` below is explicit -- erasure must name every
  store it touched, and :func:`residue` must be able to find what it missed.
- **MemCut** (arXiv 2610.21405) -- two recovery metrics that must not be
  confused. *Native recovery* is what the system's own retriever still
  returns; *residual recovery* is what a reader recovers when handed the
  surviving objects directly. A retriever that simply misses is not erasure.
  MemCut also finds candidate coverage, not selection accuracy, is the
  bottleneck, which is why :meth:`Forger.forget` cuts by predicate over whole
  stores rather than picking rows one at a time.
- **Deployment-Time Memorization** (arXiv 2606.10062) -- the Forgetting
  Residue Score, and the finding that raw-only deletion leaves derived copies
  recoverable in about 20% of cases while a full-pipeline purge or tombstone
  redaction drives residue to zero. :class:`ResidueReport` is that score.
- **SAIHM** (IETF draft-saihm-memory-protocol-03, 2026-10-11) -- erasure writes
  a receipt to a public log and appends the id to a public erasure list that
  can be rebuilt from those receipts. :class:`ReceiptLog` keeps both.
- NOESIS ``learning_journal`` and ``lesson_cue.LessonJournal`` -- append-only
  JSONL with content-addressed idempotency and a replayable projection.

Clean-room: no upstream code copied; only the methods were ported.

Governance invariants:

- This is the **only** sanctioned deletion path in the project
  (``AGENTS.md`` rule 5, as amended 2026-10-19). There is no second one.
- A tombstone records *that* something was erased, by digest and count. It
  never records the erased content, so the evidence cannot become a copy of
  the secret.
- Erasure is idempotent: re-running the same request changes nothing and
  returns the same receipt.
- Every erasure is attributable. No actor, no erasure.
- Stdlib only, no LLM anywhere.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
import uuid
from dataclasses import dataclass, field, replace
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from .atomic_write import atomic_append_line
    from .lesson_cue import Lesson
    from .text_norm import tokenize, to_ascii_fold
except ImportError:  # pragma: no cover - direct script import
    from noesis_harness.atomic_write import atomic_append_line
    from noesis_harness.lesson_cue import Lesson
    from noesis_harness.text_norm import tokenize, to_ascii_fold


SCHEMA_VERSION = "noesis.forget.v1"

#: Reason codes are string enums, not free text scattered at call sites.
REASON_USER_REQUEST = "user_request"
REASON_LEGAL_REQUEST = "legal_request"
REASON_RETENTION = "retention_policy"

REASONS = (REASON_USER_REQUEST, REASON_LEGAL_REQUEST, REASON_RETENTION)

#: Every store the erasure path knows how to reach. A store listed here and
#: not covered is a hole; a store not listed here cannot be reached at all.
STORE_MEMORY = "memory"
STORE_OBSERVATIONS = "observations"
STORE_SUMMARIES = "summaries"
STORE_GRAPH = "graph"
STORE_LESSONS = "lessons"
STORE_SKILLS = "skills"
STORE_LIBRARY = "library"
STORE_PROMOTION = "promotion"

STORES = (
    STORE_MEMORY,
    STORE_OBSERVATIONS,
    STORE_SUMMARIES,
    STORE_GRAPH,
    STORE_LESSONS,
    STORE_SKILLS,
    STORE_LIBRARY,
    STORE_PROMOTION,
)

ERASURE_TABLE = "noesis_erasure_receipts"

#: What an erased field reads as afterwards. It stands in for the content
#: rather than being empty, so a tombstone is a valid record and a reader can
#: tell "this was erased" apart from "this was never written".
ERASED_MARKER = "[erased]"

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)


class ForgetError(ValueError):
    """Raised when an erasure request is malformed or not attributable."""


def canonical(payload: Any) -> str:
    """Deterministic JSON: sorted keys, no incidental whitespace."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


#: Characters that NFKD leaves intact but that English writes in more than one
#: way. Without folding these, "Grüße" and "gruesse" would be two different
#: secrets and an erasure would only catch the spelling the requester used.
_TRANSLITERATIONS = {
    "ß": "ss",  # ß
    "æ": "ae",
    "œ": "oe",
    "ø": "o",
    "ł": "l",
    "đ": "d",
    "þ": "th",
    "ð": "d",
}


def normalize(text: str) -> str:
    """Casefold, fold accents, strip punctuation, collapse whitespace.

    Two facts that differ only in punctuation, case, diacritics or a
    transliterated character are the same fact for erasure purposes. Matching
    on the raw string would let a secret survive because someone wrote it with
    a different apostrophe.

    The transliteration runs *before* the ASCII fold on purpose: ``to_ascii_fold``
    drops a character it cannot decompose, so a sharp s would be deleted rather
    than expanded, turning "Straße" into "strae" and leaving it distinct from
    "strasse".
    """
    raw = str(text or "").casefold()
    for source, target in _TRANSLITERATIONS.items():
        raw = raw.replace(source, target)
    folded = to_ascii_fold(raw)
    return _WS.sub(" ", _PUNCT.sub(" ", folded)).strip()


def content_digest(text: str) -> str:
    """Digest of one piece of content, in its normalized form.

    Used in tombstones so the tombstone can prove *which* content was removed
    without being able to reproduce it.
    """
    return "sha256:" + hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# selection
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Predicate:
    """What to erase, expressed as a rule rather than as a list of ids.

    A predicate is the answer to MemCut's coverage problem: naming rows
    requires already knowing where the secret is, and the whole failure mode
    is that it is in more places than you looked. A predicate sweeps the store.
    """

    label: str
    tokens: Tuple[str, ...]
    scope: str = ""
    kind: str = ""
    require_all: bool = False

    def matches(self, text: str, *, scope: str = "", kind: str = "") -> bool:
        """Whether ``text`` contains any (or all) of this predicate's tokens.

        Tokens are stored digested, and the candidate is digested the same way
        before comparison -- the same digest function on both sides, so the
        request never has to hold the secret in order to match it. A predicate
        built with ``reveal_tokens=True`` stores them readable, and mixing the
        two forms is a programming error rather than a silent mismatch.
        """
        if self.scope and scope != self.scope:
            return False
        if self.kind and kind != self.kind:
            return False
        if not self.tokens:
            return False
        readable = set(tokenize(normalize(text)))
        if not readable:
            return False
        digested = any(token.startswith(_DIGEST_PREFIX) for token in self.tokens)
        if digested and not all(token.startswith(_DIGEST_PREFIX) for token in self.tokens):
            raise ForgetError("predicate_mixes_digested_and_readable_tokens")
        haystack = {_digest_token(token) for token in readable} if digested else readable
        hits = [token for token in self.tokens if token in haystack]
        if self.require_all:
            return len(hits) == len(self.tokens)
        return bool(hits)

    def reveal(self, text: str) -> str:
        """Match against readable tokens instead of digests.

        Only meaningful for a predicate built with ``reveal_tokens=True``; it
        is what lets a caller inspect what a receipt's selector actually covers
        when the selector was built from a non-sensitive phrase.
        """
        haystack = set(tokenize(normalize(text)))
        hits = [token for token in self.tokens if token in haystack]
        return ", ".join(sorted(hits))

    def fingerprint(self) -> str:
        return "sha256:" + hashlib.sha256(canonical(self.to_dict()).encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "tokens": list(self.tokens),
            "scope": self.scope,
            "kind": self.kind,
            "require_all": self.require_all,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Predicate":
        return cls(
            label=str(data.get("label") or ""),
            tokens=tuple(str(t) for t in (data.get("tokens") or ())),
            scope=str(data.get("scope") or ""),
            kind=str(data.get("kind") or ""),
            require_all=bool(data.get("require_all")),
        )


def build_predicate(
    text: str,
    *,
    label: str = "",
    scope: str = "",
    kind: str = "",
    require_all: bool = False,
    extra_tokens: Sequence[str] = (),
    reveal_tokens: bool = False,
) -> Predicate:
    """Turn a phrase into a sweep predicate over every store.

    ``require_all`` widens or narrows the sweep: false matches any listed
    token, true requires every one. For a secret, ``require_all=False`` on the
    distinctive tokens is the safe default -- it over-cuts rather than
    under-cuts, which is the direction MemCut's coverage findings point in.

    **The predicate does not keep the phrase.** Its tokens are stored as
    digests, because a predicate travels into the receipt and the receipt is
    meant to be publishable. An erasure request naming ``sk-SECRET42`` must not
    therefore leave ``sk-SECRET42`` sitting in the proof of its own removal.
    Pass ``reveal_tokens=True`` only for a non-sensitive selector, such as a
    session id, where the receipt is meant to be human-readable.
    """
    if not str(text or "").strip():
        raise ForgetError("predicate_text_required")
    raw_tokens = list(tokenize(normalize(text)))
    for extra in extra_tokens:
        # Each extra is tokenized, not taken whole. An extra written as a
        # phrase ("holder Ada Lovelace") is a phrase, and storing it as one
        # token would make it match nothing, so the widening would silently
        # do nothing at all -- the worst kind of failure in an erasure.
        for token in tokenize(normalize(str(extra or ""))):
            if token not in raw_tokens:
                raw_tokens.append(token)
    if not raw_tokens:
        raise ForgetError("predicate_has_no_searchable_tokens")
    tokens = raw_tokens if reveal_tokens else [_digest_token(token) for token in raw_tokens]
    default_label = "" if not reveal_tokens else str(text)[:60]
    return Predicate(
        label=str(label or default_label),
        tokens=tuple(sorted(set(tokens))),
        scope=str(scope or ""),
        kind=str(kind or ""),
        require_all=bool(require_all),
    )


#: Marker prefix on a digested predicate token. A predicate whose tokens are
#: all prefixed is digested; one whose tokens are all bare is revealed. Mixing
#: the two forms is refused rather than silently mismatching.
_DIGEST_PREFIX = "t:"


def _digest_token(token: str) -> str:
    """A per-token digest that still allows exact token matching.

    Hashing each token rather than the whole predicate means the sweep can
    still compare a candidate's tokens against the request -- hashing the
    request instead would make that comparison impossible without the secret.
    """
    return _DIGEST_PREFIX + hashlib.sha256(str(token).encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------------------
# receipts
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class StoreResult:
    """What happened in one store during one erasure."""

    store: str
    matched: int = 0
    removed: int = 0
    covered: bool = False
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.covered and not self.error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "store": self.store,
            "matched": self.matched,
            "removed": self.removed,
            "covered": self.covered,
            "error": self.error,
        }


@dataclass(frozen=True)
class ForgetReceipt:
    """Proof that an erasure happened, holding none of the erased content.

    Every field here is safe to publish: ids, digests, counts, reason, actor,
    time. The receipt answers "what did you delete and can you show it?" while
    being unable to reproduce what was deleted.
    """

    receipt_id: str
    request_id: str
    actor: str
    reason: str
    predicate: Predicate
    at: float
    stores: Tuple[StoreResult, ...] = ()
    request_digest: str = ""
    receipt_digest: str = ""

    @property
    def matched(self) -> int:
        return sum(s.matched for s in self.stores)

    @property
    def removed(self) -> int:
        return sum(s.removed for s in self.stores)

    @property
    def complete(self) -> bool:
        """Whether every store named in the request was actually covered."""
        return bool(self.stores) and all(s.ok for s in self.stores)

    @property
    def uncovered(self) -> Tuple[str, ...]:
        return tuple(s.store for s in self.stores if not s.ok)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "request_id": self.request_id,
            "actor": self.actor,
            "reason": self.reason,
            "predicate": self.predicate.to_dict(),
            "at": self.at,
            "stores": [s.to_dict() for s in self.stores],
            "matched": self.matched,
            "removed": self.removed,
            "complete": self.complete,
            "uncovered": list(self.uncovered),
            "request_digest": self.request_digest,
            "receipt_digest": self.receipt_digest or self.compute_digest(),
        }

    def compute_digest(self) -> str:
        body = {
            "request_id": self.request_id,
            "actor": self.actor,
            "reason": self.reason,
            "predicate": self.predicate.fingerprint(),
            "at": self.at,
            "stores": [s.to_dict() for s in self.stores],
        }
        return "sha256:" + hashlib.sha256(canonical(body).encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ForgetReceipt":
        return cls(
            receipt_id=str(data.get("receipt_id") or ""),
            request_id=str(data.get("request_id") or ""),
            actor=str(data.get("actor") or ""),
            reason=str(data.get("reason") or ""),
            predicate=Predicate.from_dict(data.get("predicate") or {}),
            at=float(data.get("at") or 0.0),
            stores=tuple(
                StoreResult(
                    store=str(s.get("store") or ""),
                    matched=int(s.get("matched") or 0),
                    removed=int(s.get("removed") or 0),
                    covered=bool(s.get("covered")),
                    error=str(s.get("error") or ""),
                )
                for s in (data.get("stores") or ())
            ),
            request_digest=str(data.get("request_digest") or ""),
            receipt_digest=str(data.get("receipt_digest") or ""),
        )


# --------------------------------------------------------------------------
# residue
# --------------------------------------------------------------------------


@dataclass
class ResidueReport:
    """What is still extractable after an erasure -- the honest answer.

    ``native_hits`` is what this system's own recall still returns;
    ``residual_hits`` is what a reader recovers when handed every surviving
    object directly. MemCut's point is that the gap between the two is the
    hidden-risk share: evidence the store still holds that the retriever
    happens not to surface today.
    """

    request_id: str
    native_hits: List[str] = field(default_factory=list)
    residual_hits: List[str] = field(default_factory=list)
    stores_scanned: Tuple[str, ...] = ()

    @property
    def clean(self) -> bool:
        return not self.native_hits and not self.residual_hits

    @property
    def hidden_risk(self) -> float:
        """Share of residual successes the retriever did not surface.

        A lower bound on the share of recoverable evidence that ordinary
        retrieval would have missed. Non-zero means the erasure is not
        trustworthy, however quiet the retriever happens to be today.
        """
        if not self.residual_hits:
            return 0.0
        return max(0, len(self.residual_hits) - len(self.native_hits)) / float(len(self.residual_hits))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "request_id": self.request_id,
            "native_hits": list(self.native_hits),
            "residual_hits": list(self.residual_hits),
            "stores_scanned": list(self.stores_scanned),
            "clean": self.clean,
            "hidden_risk": round(self.hidden_risk, 4),
            "native_count": len(self.native_hits),
            "residual_count": len(self.residual_hits),
        }


# --------------------------------------------------------------------------
# coverage
# --------------------------------------------------------------------------


class _Store:
    """One reachable store. A subclass implements ``sweep``; nothing else."""

    name = ""

    def available(self) -> bool:
        return False

    def sweep(self, predicate: Predicate) -> Tuple[int, int, str]:
        """Return ``(matched, removed, error)``."""
        raise NotImplementedError

    def survivors(self, predicate: Predicate) -> List[str]:
        """Every surviving record that still matches, whatever its store."""
        return []

    def native_hits(self, predicate: Predicate) -> List[str]:
        """What this store's own read path still returns for the predicate."""
        return []


class _MemoryStore(_Store):
    name = STORE_MEMORY

    def __init__(self, memory: Any) -> None:
        self.memory = memory

    def available(self) -> bool:
        return self.memory is not None

    def _rows(self):
        with self.memory._conn() as c:
            return c.execute("SELECT id, fact, kind FROM memories").fetchall()

    def sweep(self, predicate: Predicate) -> Tuple[int, int, str]:
        try:
            matched = [r for r in self._rows() if predicate.matches(r["fact"], kind=r["kind"])]
            if not matched:
                return 0, 0, ""
            with self.memory._lock, self.memory._conn() as c:
                for row in matched:
                    # mem_fts rows go with the parent row via the AFTER DELETE
                    # trigger; the embedding is a column on the same row.
                    c.execute("DELETE FROM memories WHERE id=?", (row["id"],))
            return len(matched), len(matched), ""
        except Exception as exc:
            return 0, 0, "%s: %s" % (type(exc).__name__, exc)

    def survivors(self, predicate: Predicate) -> List[str]:
        try:
            return [r["id"] for r in self._rows() if predicate.matches(r["fact"], kind=r["kind"])]
        except Exception:
            return []

    def native_hits(self, predicate: Predicate) -> List[str]:
        """What recall itself still returns for the erased content.

        Deliberately goes through the public read path rather than the table:
        an erasure that only cleans the table while recall still serves the
        content is not an erasure. The query is built from the fact text of
        whatever still matches, because the predicate's own tokens are
        digests and a digest is not searchable text.
        """
        try:
            survivors = []
            with self.memory._conn() as c:
                rows = c.execute("SELECT id, fact, kind FROM memories").fetchall()
            for row in rows:
                if predicate.matches(row["fact"], kind=row["kind"]):
                    survivors.append(row)
            if not survivors:
                return []
            probe = " ".join(tokenize(normalize(survivors[0]["fact"]))) or " "
            hits = self.memory.recall(probe, limit=50)
        except Exception:
            return []
        return [
            str(hit.get("id"))
            for hit in hits
            if predicate.matches(str(hit.get("fact", "")), kind=str(hit.get("kind", "")))
        ]


class _ObservationStore(_Store):
    name = STORE_OBSERVATIONS

    def __init__(self, memory: Any) -> None:
        self.memory = memory

    def available(self) -> bool:
        return self.memory is not None

    def _rows(self):
        with self.memory._conn() as c:
            return c.execute("SELECT id, content, session_id FROM observations").fetchall()

    def sweep(self, predicate: Predicate) -> Tuple[int, int, str]:
        try:
            matched = [r for r in self._rows() if predicate.matches(r["content"])]
            if not matched:
                return 0, 0, ""
            with self.memory._lock, self.memory._conn() as c:
                for row in matched:
                    c.execute("DELETE FROM observations WHERE id=?", (row["id"],))
            return len(matched), len(matched), ""
        except Exception as exc:
            return 0, 0, "%s: %s" % (type(exc).__name__, exc)

    def survivors(self, predicate: Predicate) -> List[str]:
        try:
            return [r["id"] for r in self._rows() if predicate.matches(r["content"])]
        except Exception:
            return []


class _SummaryStore(_Store):
    name = STORE_SUMMARIES

    def __init__(self, memory: Any) -> None:
        self.memory = memory

    def available(self) -> bool:
        return self.memory is not None

    def _rows(self):
        with self.memory._conn() as c:
            return c.execute("SELECT id, text FROM summaries").fetchall()

    def sweep(self, predicate: Predicate) -> Tuple[int, int, str]:
        try:
            matched = [r for r in self._rows() if predicate.matches(r["text"])]
            if not matched:
                return 0, 0, ""
            with self.memory._lock, self.memory._conn() as c:
                for row in matched:
                    c.execute("DELETE FROM summaries WHERE id=?", (row["id"],))
            return len(matched), len(matched), ""
        except Exception as exc:
            return 0, 0, "%s: %s" % (type(exc).__name__, exc)

    def survivors(self, predicate: Predicate) -> List[str]:
        try:
            return [r["id"] for r in self._rows() if predicate.matches(r["text"])]
        except Exception:
            return []


class _GraphStore(_Store):
    name = STORE_GRAPH

    def __init__(self, graph: Any) -> None:
        self.graph = graph

    def available(self) -> bool:
        return self.graph is not None

    def _rows(self):
        with self.graph._conn() as c:
            return c.execute("SELECT id, subj, pred, obj FROM edges").fetchall()

    @staticmethod
    def _joined(row: Any) -> str:
        return "%s %s %s" % (row["subj"], row["pred"], row["obj"])

    def sweep(self, predicate: Predicate) -> Tuple[int, int, str]:
        # An edge carries the secret spread over three columns, so the sweep
        # runs on the joined text: matching one column alone would leave the
        # edge intact and still leaking.
        try:
            matched = [r for r in self._rows() if predicate.matches(self._joined(r))]
            if not matched:
                return 0, 0, ""
            with self.graph._lock, self.graph._conn() as c:
                for row in matched:
                    c.execute("DELETE FROM edges WHERE id=?", (row["id"],))
            return len(matched), len(matched), ""
        except Exception as exc:
            return 0, 0, "%s: %s" % (type(exc).__name__, exc)

    def survivors(self, predicate: Predicate) -> List[str]:
        try:
            return [r["id"] for r in self._rows() if predicate.matches(self._joined(r))]
        except Exception:
            return []


class _LessonStore(_Store):
    """Erasure of the append-only lesson journal.

    The lesson journal is append-only by design, so this is the one store
    where erasure is a *supersede*, not a delete: the record stays, marked
    erased, carrying no content. An append-only log cannot be rewritten to
    remove a line without breaking its own replay digest, so the honest move
    is to append the erasure and let the read path honour it.
    """

    name = STORE_LESSONS

    def __init__(self, journal: Any) -> None:
        self.journal = journal

    def available(self) -> bool:
        return self.journal is not None

    def _matching(self, predicate: Predicate) -> List[Any]:
        """Current lessons whose text still matches, deduplicated by id.

        Matched against the *projection* rather than against the raw log: a
        lesson that was already superseded must not be re-erased, and a lesson
        that was promoted must still be caught even though its only log line is
        the promotion.
        """
        try:
            state = self.journal.current()
        except Exception:
            return []
        matched = []
        for lesson_id in sorted(state):
            lesson = state[lesson_id]
            if predicate.matches(" ".join((lesson.cue, lesson.lesson, lesson.evidence))):
                matched.append(lesson)
        return matched

    def sweep(self, predicate: Predicate) -> Tuple[int, int, str]:
        try:
            matched = self._matching(predicate)
            if not matched:
                return 0, 0, ""
            erased = 0
            for lesson in matched:
                blanked = Lesson(
                    **{
                        **{
                            key: getattr(lesson, key)
                            for key in (
                                "lesson_id",
                                "domain",
                                "confidence",
                                "scope",
                                "sensitivity",
                                "source_ids",
                                "status",
                                "created_at",
                                "provenance_digest",
                                "supersedes",
                            )
                        },
                        # The content is replaced, not deleted: the append-only
                        # log keeps its line and its replay digest, and the
                        # lesson stops matching because there is nothing left
                        # in it to match. A tombstone marker rather than an
                        # empty string, because a Lesson with an empty cue is
                        # malformed and must not be constructible -- the type
                        # refuses to represent "no lesson", which is exactly
                        # the state erasure creates.
                        "cue": ERASED_MARKER,
                        "lesson": ERASED_MARKER,
                        "evidence": ERASED_MARKER,
                    }
                )
                self.journal.record(
                    blanked,
                    "erase",
                    actor="forget",
                    reason="predicate:%s" % predicate.fingerprint(),
                    at=lesson.created_at,
                )
                erased += 1
            return len(matched), erased, ""
        except Exception as exc:
            return 0, 0, "%s: %s" % (type(exc).__name__, exc)

    def survivors(self, predicate: Predicate) -> List[str]:
        return [lesson.lesson_id for lesson in self._matching(predicate)]


# --------------------------------------------------------------------------
# filesystem and sqlite-backed stores
# --------------------------------------------------------------------------


class _FileStore(_Store):
    """Shared behaviour for stores that are directories of text files.

    Erasure here is a rewrite, not a removal: the file keeps its name and a
    tombstone body, so a reader can still see that something was there and
    when it went, while the content is gone. Removing the file outright would
    also delete the evidence, which is the opposite of what an erasure receipt
    needs.
    """

    name = ""

    def __init__(self, root: Any) -> None:
        self.root = root

    def available(self) -> bool:
        return self.root is not None

    def _files(self):
        raise NotImplementedError

    def _rewrite(self, path: Any, predicate: Predicate) -> None:
        raise NotImplementedError

    def sweep(self, predicate: Predicate) -> Tuple[int, int, str]:
        try:
            matched = 0
            rewritten = 0
            for path, body in self._files():
                if not predicate.matches(body):
                    continue
                matched += 1
                self._rewrite(path, predicate)
                rewritten += 1
            return matched, rewritten, ""
        except Exception as exc:
            return 0, 0, "%s: %s" % (type(exc).__name__, exc)

    def survivors(self, predicate: Predicate) -> List[str]:
        try:
            return [str(path) for path, body in self._files() if predicate.matches(body)]
        except Exception:
            return []


class _SkillStore(_FileStore):
    """Installed skill content, across *every* version on disk.

    Sweeping only the active version would be the obvious bug here: a rollback
    target still carries the content, so a secret in a superseded skill would
    survive an erasure that reported itself complete.
    """

    name = STORE_SKILLS

    def _files(self):
        root = getattr(self.root, "root", None)
        if root is None:
            return
        for path in sorted(root.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            if path.name in ("active.json", "ACTIVE", "ACTIVE.next"):
                continue  # pointers hold ids and digests, never content
            try:
                yield path, path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

    def _rewrite(self, path, predicate):
        body = ERASED_BODY % content_digest(
            " ".join(str(t) for t in predicate.tokens if not str(t).startswith(_DIGEST_PREFIX))
            or "erased"
        )
        temporary = path.with_name(path.name + ".erasing")
        temporary.write_text(body, encoding="utf-8")
        os.replace(str(temporary), str(path))
        fsync_paths([str(path)])


class _LibraryStore(_Store):
    """Adopted artifacts in a domain library.

    The library keeps full artifact trees, so a secret planted in an adopted
    document is still readable long after the lesson that referenced it was
    superseded. Entry metadata is tombstoned and the index is rebuilt, so a
    later reader cannot be handed the content by following a stale pointer.
    """

    name = STORE_LIBRARY

    def __init__(self, library: Any) -> None:
        self.library = library

    def available(self) -> bool:
        return self.library is not None

    def _files(self):
        directory = getattr(self.library, "dir", None)
        if directory is None or not directory.is_dir():
            return
        for path in sorted(directory.rglob("*")):
            if not path.is_file():
                continue
            try:
                yield path, path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

    def sweep(self, predicate: Predicate) -> Tuple[int, int, str]:
        matched = 0
        rewritten = 0
        try:
            for path, body in self._files():
                if not predicate.matches(body):
                    continue
                matched += 1
                if path.name == "INDEX.md":
                    # The index is a navigation aid over the entries, not a
                    # record; it is regenerated from them below. Rewriting it
                    # to a tombstone would just be overwritten.
                    continue
                if path.name == "entry.json":
                    # The entry is structured data. It must stay parseable, or
                    # rebuild_index() cannot see the entry at all and the
                    # library silently reports itself empty -- which is how a
                    # tombstoned entry becomes an entry that looks like it
                    # never existed.
                    self._tombstone_entry(path, body, predicate)
                    rewritten += 1
                    continue
                temporary = path.with_name(path.name + ".erasing")
                temporary.write_text(ERASED_BODY % content_digest(body), encoding="utf-8")
                os.replace(str(temporary), str(path))
                fsync_paths([str(path)])
                rewritten += 1
            rebuild = getattr(self.library, "rebuild_index", None)
            if callable(rebuild):
                rebuild()
            return matched, rewritten, ""
        except Exception as exc:
            return matched, rewritten, "%s: %s" % (type(exc).__name__, exc)

    @staticmethod
    def _tombstone_entry(path, body, predicate) -> None:
        """Blank an entry's text fields while keeping its structure and id."""
        try:
            payload = json.loads(body)
        except ValueError:
            payload = {}
        payload["cue"] = ERASED_MARKER
        payload["why"] = ERASED_MARKER
        payload["artifacts"] = []
        if isinstance(payload.get("lesson"), dict):
            payload["lesson"] = None
        payload["erased"] = True
        payload["erasure_digest"] = content_digest(body)
        temporary = path.with_name(path.name + ".erasing")
        temporary.write_text(canonical(payload), encoding="utf-8")
        os.replace(str(temporary), str(path))

    def survivors(self, predicate: Predicate) -> List[str]:
        out: List[str] = []
        try:
            for path, body in self._files():
                if predicate.matches(body) and ERASED_MARKER not in body:
                    out.append(str(path))
        except Exception:
            pass
        return out


class _PromotionStore(_Store):
    """The promotion state database.

    Every governance row stores its payload as one JSON blob in a
    ``record_json`` column, so the sweep reads and rewrites the column rather
    than trying to address individual fields inside it. Rewriting to a
    tombstone keeps the row, its id and its signed-receipt linkage intact --
    which matters, because a promotion receipt that vanished would be
    indistinguishable from one that never happened.
    """

    name = STORE_PROMOTION

    #: Tables whose payload column can carry user content.
    PAYLOAD_TABLES = (
        ("promotion_receipts", "receipt_id", "record_json"),
        ("promotion_evaluations", "evaluation_id", "record_json"),
        ("promotion_proposals", "proposal_id", "record_json"),
        ("promotion_activation_journal", "proposal_id", "record_json"),
    )

    def __init__(self, state: Any) -> None:
        self.state = state

    def available(self) -> bool:
        return self.state is not None

    def _connect(self):
        return self.state._connect()

    def _existing(self):
        with self._connect() as db:
            names = {
                str(row[0])
                for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            }
        return [t for t in self.PAYLOAD_TABLES if t[0] in names]

    def sweep(self, predicate: Predicate) -> Tuple[int, int, str]:
        try:
            matched = 0
            rewritten = 0
            for table, id_column, payload_column in self._existing():
                with self._connect() as db:
                    rows = db.execute(
                        "SELECT %s AS rid, %s AS body FROM %s" % (id_column, payload_column, table)
                    ).fetchall()
                for row in rows:
                    body = str(row["body"] or "")
                    if not predicate.matches(body):
                        continue
                    matched += 1
                    tombstone = canonical(
                        {"erased": True, "digest": content_digest(body), "id": str(row["rid"])}
                    )
                    with self._connect() as db:
                        db.execute(
                            "UPDATE %s SET %s=? WHERE %s=?" % (table, payload_column, id_column),
                            (tombstone, str(row["rid"])),
                        )
                    rewritten += 1
            return matched, rewritten, ""
        except Exception as exc:
            return 0, 0, "%s: %s" % (type(exc).__name__, exc)

    def survivors(self, predicate: Predicate) -> List[str]:
        out: List[str] = []
        try:
            for table, id_column, payload_column in self._existing():
                with self._connect() as db:
                    rows = db.execute(
                        "SELECT %s AS rid, %s AS body FROM %s" % (id_column, payload_column, table)
                    ).fetchall()
                for row in rows:
                    body = str(row["body"] or "")
                    if predicate.matches(body) and '"erased": true' not in body:
                        out.append("%s:%s" % (table, row["rid"]))
        except Exception:
            pass
        return out


# --------------------------------------------------------------------------
# raw residue: bytes, not rows
# --------------------------------------------------------------------------

#: Body written in place of erased file content.
ERASED_BODY = (
    "[erased]\n"
    "This file's content was removed by an erasure request.\n"
    "d9j9d1ffstub: %s\n"
)


#: Sibling files SQLite creates next to a database. Each can hold a copy of
#: the content, and a checkpoint only truncates the WAL -- it does not touch a
#: rollback journal left by an interrupted transaction.
SQLITE_SIDECARS = ("-wal", "-shm", "-journal")


def sqlite_sidecars(db_path: str) -> List[str]:
    """Every sibling file that could carry the database's content."""
    return [db_path + suffix for suffix in SQLITE_SIDECARS if os.path.exists(db_path + suffix)]


def scrub_sidecars(db_path: str) -> Dict[str, Any]:
    """Overwrite and remove the WAL, SHM and rollback journal of a database.

    ``wal_checkpoint(TRUNCATE)`` truncates the WAL to zero but leaves the file,
    and it does not touch ``-journal`` at all. A rollback journal from an
    interrupted transaction can hold the pre-deletion page images, which is a
    copy of exactly what was erased. This removes them.
    """
    result: Dict[str, Any] = {"db_path": db_path, "removed": [], "kept": []}
    for path in sqlite_sidecars(db_path):
        try:
            size = os.path.getsize(path)
            if size:
                with open(path, "r+b") as handle:
                    handle.write(b"\x00" * size)
                    handle.flush()
                    os.fsync(handle.fileno())
            os.remove(path)
            result["removed"].append(os.path.basename(path))
        except OSError as exc:
            result["kept"].append("%s: %s" % (os.path.basename(path), exc))
    return result


def harden_sqlite(db_path: str) -> Dict[str, Any]:
    """Make a SQLite file as close to unrecoverable as the stdlib allows.

    Three pragmas, each with a distinct job:

    - ``secure_delete=ON`` zeroes freed space instead of leaving the old bytes
      in the page. SQLite 3.42+ defaults this on; setting it explicitly is what
      makes the behaviour independent of the host's SQLite build, which is the
      only thing that makes a claim portable.
    - ``wal_checkpoint(TRUNCATE)`` folds the write-ahead log back into the
      database and truncates it, because a deleted row can otherwise survive in
      a WAL segment even when the main file is clean.
    - ``VACUUM`` rebuilds the file, so freelists and overflow pages from before
      the erasure are not carried forward.

    None of this is cryptographic erasure. See :class:`CellCipher`.
    """
    db_path = str(db_path)
    result: Dict[str, Any] = {"db_path": db_path, "applied": []}
    if not os.path.isfile(db_path):
        result["error"] = "not_a_file"
        return result
    wal = db_path + "-wal"
    had_wal = os.path.exists(wal)
    wal_size = os.path.getsize(wal) if had_wal else 0
    # Record what was present before anything opens the database. SQLite
    # recovers and removes a valid WAL on open, so a report written afterwards
    # would credit the scrubber for work SQLite did -- or, worse, claim nothing
    # was there.
    present_before = sqlite_sidecars(db_path)
    try:
        db = sqlite3.connect(db_path, timeout=10)
        try:
            db.execute("PRAGMA secure_delete=ON")
            result["secure_delete"] = db.execute("PRAGMA secure_delete").fetchone()[0]
            result["applied"].append("secure_delete")
            db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            result["applied"].append("wal_checkpoint_truncate")
            db.commit()
            db.execute("VACUUM")
            result["applied"].append("vacuum")
            db.commit()
        finally:
            db.close()
    except Exception as exc:
        result["error"] = "%s: %s" % (type(exc).__name__, exc)
        return result
    result["wal_bytes_before"] = wal_size
    result["wal_bytes_after"] = os.path.getsize(wal) if os.path.exists(wal) else 0
    # The checkpoint truncates the WAL but leaves the file, and does not touch
    # a rollback journal. Scrub both, because either can hold a page image of
    # the content that was just erased.
    sidecars = scrub_sidecars(db_path)
    sidecars["present_before"] = [os.path.basename(path) for path in present_before]
    sidecars["vanished_on_open"] = [
        os.path.basename(path)
        for path in present_before
        if not os.path.exists(path) and os.path.basename(path) not in sidecars["removed"]
    ]
    sidecars["removed"] = sidecars["removed"] + sidecars.pop("vanished_on_open")
    result["sidecars"] = sidecars
    return result


def fsync_paths(paths: Sequence[str]) -> Dict[str, Any]:
    """Flush file and directory metadata to the storage device.

    A rewrite is not durable until the device says so. Without this, an
    erasure receipt can be true of the page cache and false of the disk after
    a crash. Directory entries are fsynced too, because replacing a file
    updates its directory entry, not only its contents.
    """
    report: Dict[str, Any] = {"fsynced": [], "errors": []}
    seen = set()
    for path in paths:
        if not path or path in seen:
            continue
        seen.add(path)
        targets = [path]
        directory = os.path.dirname(os.path.abspath(path))
        if directory not in seen:
            seen.add(directory)
            targets.append(directory)
        for target in targets:
            try:
                descriptor = os.open(target, os.O_RDONLY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
                report["fsynced"].append(target)
            except OSError as exc:
                report["errors"].append("%s: %s" % (target, exc))
    return report


def scan_raw_bytes(paths: Sequence[str], needle: str) -> Dict[str, Any]:
    """Search the raw bytes of files for a phrase the logical layer forgot.

    This is the check that would catch the failure the logical report cannot
    see: a row deleted cleanly while its bytes remain in a page, a WAL segment
    or an overwritten-but-not-truncated file. It reads bytes, not records, and
    it deliberately does not care whether anything is still queryable.

    Matching is on the raw needle as well as on its normalized form, because
    what survives on disk is usually the bytes that were written -- unnormalized,
    with original punctuation.
    """
    forms = {str(needle or "")}
    folded = normalize(needle)
    if folded:
        forms.add(folded)
        forms.add(folded.replace(" ", ""))
        # On disk the original bytes are usually unnormalized, so a phrase is
        # also searched token by token: "SK COVER42" must find the stored
        # "sk-COVER42" however the punctuation survived. A single distinctive
        # token is the unit that actually persists in a page.
        for token in tokenize(folded):
            if len(token) >= 4:
                forms.add(token)
    forms = {f for f in forms if f}
    needles = [(form, form.encode("utf-8")) for form in sorted(forms)]
    hits: List[Dict[str, Any]] = []
    scanned = 0
    for path in paths:
        try:
            if os.path.isdir(path):
                candidates = [
                    os.path.join(root, name)
                    for root, _dirs, names in os.walk(path)
                    for name in names
                ]
            else:
                candidates = [path]
            for candidate in candidates:
                if not os.path.isfile(candidate) or "__pycache__" in candidate:
                    continue
                scanned += 1
                with open(candidate, "rb") as handle:
                    blob = handle.read()
                lowered = blob.lower()
                for form, needle_bytes in needles:
                    offset = lowered.find(needle_bytes.lower())
                    if offset >= 0:
                        hits.append(
                            {
                                "path": str(candidate),
                                "offset": offset,
                                "form": form,
                                "form_length": len(needle_bytes),
                                "size": len(blob),
                            }
                        )
                        break
        except OSError:
            continue
    return {
        "files_scanned": scanned,
        "needle_forms": sorted(forms),
        "hits": hits,
        "raw_residue": bool(hits),
    }


# --------------------------------------------------------------------------
# the cryptographic boundary
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class CipherCapability:
    """What this build can do, and what it has actually done.

    SAIHM defines two erasure classes. Cryptographic erasure destroys the
    wrapping key, after which the ciphertext is unreadable by anyone including
    the operator. Access-control erasure only withdraws access.

    Two separate answers, deliberately kept apart:

    - ``cipher_class`` -- whether a cipher exists at all here. Raised only
      after the RFC 8439 vectors pass on this interpreter.
    - ``erasure_class`` -- what a store has actually done. ``cell_cipher.py``
      exists and is verified, but a store that never called ``CellCipher`` has
      only swept rows, and sweeping rows is access control however good the
      cipher sitting unused beside it.

    Collapsing these into one field would let an unused cipher make a database
    deletion claim cryptographic erasure. ``AGENTS.md`` forbids exactly that,
    so the report cannot express it.
    """

    kdf_available: bool = True
    symmetric_cipher_available: bool = False
    aead_available: bool = False
    cipher_class: str = "access_control"
    erasure_class: str = "access_control"
    sealed: bool = False
    sealed_cells: int = 0
    stdlib_only: bool = True
    cipher: str = ""
    selftest_passed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kdf_available": self.kdf_available,
            "symmetric_cipher_available": self.symmetric_cipher_available,
            "aead_available": self.aead_available,
            "cipher_class": self.cipher_class,
            "erasure_class": self.erasure_class,
            "sealed": self.sealed,
            "sealed_cells": self.sealed_cells,
            "stdlib_only": self.stdlib_only,
            "cipher": self.cipher,
            "selftest_passed": self.selftest_passed,
            "logical_erasure_only": self.erasure_class != "cryptographic",
            "note": (
                "ChaCha20-Poly1305 is implemented in aead.py from RFC 8439 and "
                "checked against every published test vector. A store that "
                "seals cells under per-cell keys (cell_cipher.py) can therefore "
                "perform cryptographic erasure. A store that does not is only "
                "access-control erased, however clean its residue report and "
                "however ready the unused cipher beside it."
            ),
        }


def cipher_capability(
    *, sealed_cells: int = 0, sealed: Optional[bool] = None
) -> CipherCapability:
    """Report cipher readiness and, separately, whether anything is sealed.

    ``sealed_cells`` is the only thing that raises ``erasure_class``. Passing
    nothing reports access-control, because the default state of a store that
    has not been asked to seal anything is *not sealed*, not *sealed*.
    """
    try:
        from .aead import selftest
    except ImportError:  # pragma: no cover - direct script import
        from noesis_harness.aead import selftest

    report = selftest()
    passed = bool(report.get("all_passed"))
    count = int(sealed_cells)
    is_sealed = bool(sealed) if sealed is not None else count > 0
    cryptographic = passed and is_sealed and count > 0
    return CipherCapability(
        kdf_available=bool(getattr(hashlib, "scrypt", None)),
        symmetric_cipher_available=passed,
        aead_available=passed,
        cipher_class="cryptographic" if passed else "access_control",
        erasure_class="cryptographic" if cryptographic else "access_control",
        sealed=is_sealed and count > 0,
        sealed_cells=count,
        cipher=str(report.get("algorithm") or ""),
        selftest_passed=passed,
    )


# --------------------------------------------------------------------------
# receipt log
# --------------------------------------------------------------------------


class ReceiptLog:
    """Append-only receipts plus the public erasure list, per SAIHM.

    Two artifacts, both rebuildable from the other: every erasure appends a
    receipt, and appends its id to an erasure list that an observer can
    reconstruct from the receipts. Keeping both is what turns "we deleted
    your data" from a claim into something checkable.
    """

    def __init__(self, path: str) -> None:
        self.path = str(path)

    @property
    def list_path(self) -> str:
        return self.path + ".erasure-list"

    def append(self, receipt: ForgetReceipt) -> str:
        line = canonical(receipt.to_dict())
        atomic_append_line(self.path, line)
        if receipt.receipt_id not in self.receipt_ids():
            atomic_append_line(self.list_path, receipt.receipt_id + "\n")
        return receipt.receipt_id

    def receipts(self) -> List[ForgetReceipt]:
        out: List[ForgetReceipt] = []
        try:
            handle = open(self.path, "r", encoding="utf-8")
        except OSError:
            return out
        with handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(ForgetReceipt.from_dict(json.loads(line)))
                except (ValueError, KeyError, TypeError):
                    continue
        return out

    def receipt_ids(self) -> List[str]:
        try:
            handle = open(self.list_path, "r", encoding="utf-8")
        except OSError:
            return []
        with handle:
            return [line.strip() for line in handle if line.strip()]

    def find(self, request_id: str) -> Optional[ForgetReceipt]:
        for receipt in self.receipts():
            if receipt.request_id == request_id:
                return receipt
        return None

    def verify_list(self) -> Dict[str, Any]:
        """Whether the public list still agrees with the receipts.

        The list is derived, so this is a consistency check rather than a
        security control: it catches a truncated or hand-edited list, which is
        exactly the failure an observer would notice.
        """
        from_receipts = {r.receipt_id for r in self.receipts()}
        from_list = set(self.receipt_ids())
        return {
            "receipts": len(from_receipts),
            "listed": len(from_list),
            "missing_from_list": sorted(from_receipts - from_list),
            "missing_receipt": sorted(from_list - from_receipts),
            "consistent": from_receipts == from_list,
        }


# --------------------------------------------------------------------------
# forger
# --------------------------------------------------------------------------


class Forger:
    """Erase by predicate across every store, leave proof, report the residue."""

    def __init__(
        self,
        memory: Any = None,
        *,
        graph: Any = None,
        lesson_journal: Any = None,
        skill_store: Any = None,
        domain_library: Any = None,
        promotion_state: Any = None,
        receipt_path: str = "",
        clock: Optional[Callable[[], float]] = None,
        harden: bool = True,
        durable: bool = True,
    ) -> None:
        self.clock = clock or time.time
        self.harden = bool(harden)
        self.stores: List[_Store] = []
        if memory is not None:
            self.stores.extend(
                [_MemoryStore(memory), _ObservationStore(memory), _SummaryStore(memory)]
            )
        if graph is not None:
            self.stores.append(_GraphStore(graph))
        if lesson_journal is not None:
            self.stores.append(_LessonStore(lesson_journal))
        if skill_store is not None:
            self.stores.append(_SkillStore(skill_store))
        if domain_library is not None:
            self.stores.append(_LibraryStore(domain_library))
        if promotion_state is not None:
            self.stores.append(_PromotionStore(promotion_state))
        self.log = ReceiptLog(receipt_path) if receipt_path else None
        #: Backup locations this process cannot reach. Declared rather than
        #: assumed, so a receipt can say what it does not cover.
        self.backup_roots: List[str] = []
        #: Whether erasure flushes to the storage device. On by default: a
        #: rewrite is not durable until the device says so.
        self.durable = bool(durable)

    # -- hardening ---------------------------------------------------------

    def sqlite_paths(self) -> Tuple[str, ...]:
        """Every SQLite file this forger can reach, including WAL siblings."""
        paths: List[str] = []
        for candidate in (
            getattr(self.stores[0].memory, "db_path", None) if self.stores else None,
            getattr(getattr(self, "promotion_state", None), "path", None),
        ):
            if candidate:
                paths.append(str(candidate))
                paths.append(str(candidate) + "-wal")
                paths.append(str(candidate) + "-shm")
        seen: List[str] = []
        for path in paths:
            if path not in seen:
                seen.append(path)
        return tuple(seen)

    def harden_databases(self) -> List[Dict[str, Any]]:
        """Run :func:`harden_sqlite` over every reachable database."""
        return [harden_sqlite(path) for path in self.sqlite_paths()]

    def declare_backups(self, roots: Sequence[str]) -> List[str]:
        """Register backup locations this process cannot reach but must report.

        A library cannot delete a replica it does not own. What it *can* do is
        refuse to let a receipt imply that it did. Declared roots are carried
        on every subsequent receipt and counted in the residue report, so an
        operator reading a "complete" erasure sees the places it does not
        cover rather than inferring there are none.
        """
        declared = [str(root) for root in roots if str(root or "").strip()]
        for root in declared:
            if root not in self.backup_roots:
                self.backup_roots.append(root)
        return list(self.backup_roots)

    def reachable_backups(self) -> List[str]:
        """Declared backup roots that exist on this filesystem and are readable."""
        return [root for root in self.backup_roots if os.path.exists(root)]

    def scan_backups(self, needle: str) -> Dict[str, Any]:
        """Scan the declared backup roots that this process can actually read.

        Replicas that are absent, remote or permission-denied are reported as
        *unreached* rather than passed over. "I could not look" and "I looked
        and found nothing" are different answers, and a receipt that conflates
        them is the failure this method exists to prevent.
        """
        reachable = self.reachable_backups()
        report = scan_raw_bytes(reachable, needle) if reachable else {
            "files_scanned": 0,
            "needle_forms": [],
            "hits": [],
            "raw_residue": False,
        }
        report["declared"] = list(self.backup_roots)
        report["reached"] = reachable
        report["unreached"] = [root for root in self.backup_roots if root not in reachable]
        report["complete_coverage"] = bool(self.backup_roots) and not report["unreached"]
        return report

    def raw_residue(self, needle: str, extra_paths: Sequence[str] = ()) -> Dict[str, Any]:
        """Search the raw bytes of every reachable file for ``needle``.

        The logical residue report cannot see a row whose bytes linger in a
        freed page or a WAL segment. This can. A non-empty result means the
        erasure reached every row and still left the content on disk, which is
        exactly the claim a sweep must not make silently.
        """
        paths = list(self.sqlite_paths()) + [str(p) for p in extra_paths]
        paths.append(self.log.path) if self.log is not None else None
        return scan_raw_bytes(paths, needle)

    @property
    def covered_stores(self) -> Tuple[str, ...]:
        return tuple(store.name for store in self.stores)

    def forget(
        self,
        predicate: Predicate,
        *,
        actor: str,
        reason: str = REASON_USER_REQUEST,
        request_id: str = "",
    ) -> ForgetReceipt:
        """Erase everything matching ``predicate`` and return the proof.

        Idempotent by ``request_id``: repeating a request returns the original
        receipt instead of erasing again. Without an explicit ``request_id``
        one is derived from the predicate, the actor and the reason, so the
        same erasure asked twice is still one erasure.
        """
        if not str(actor).strip():
            raise ForgetError("actor_required_erasure_must_be_attributable")
        if reason not in REASONS:
            raise ForgetError("unknown_reason")
        if not predicate.tokens:
            raise ForgetError("predicate_has_no_tokens")

        request = str(request_id or "") or "req_" + hashlib.sha256(
            canonical([predicate.fingerprint(), actor, reason]).encode("utf-8")
        ).hexdigest()[:24]

        if self.log is not None:
            existing = self.log.find(request)
            if existing is not None:
                return existing

        at = float(self.clock())
        results: List[StoreResult] = []
        for store in self.stores:
            try:
                matched, removed, error = store.sweep(predicate)
            except Exception as exc:  # a store that blows up is an uncovered store
                results.append(
                    StoreResult(
                        store=store.name,
                        covered=False,
                        error="%s: %s" % (type(exc).__name__, exc),
                    )
                )
                continue
            results.append(
                StoreResult(
                    store=store.name,
                    matched=matched,
                    removed=removed,
                    covered=True,
                    error=error,
                )
            )

        receipt = ForgetReceipt(
            receipt_id="frc_" + hashlib.sha256(
                canonical([request, at, [s.to_dict() for s in results]]).encode("utf-8")
            ).hexdigest()[:24],
            request_id=request,
            actor=str(actor),
            reason=str(reason),
            predicate=predicate,
            at=at,
            stores=tuple(results),
            request_digest=predicate.fingerprint(),
        )
        # Filled in now rather than lazily, so a receipt handed back to a
        # caller already carries its own integrity digest.
        receipt = replace(receipt, receipt_digest=receipt.compute_digest())
        if self.log is not None:
            self.log.append(receipt)
        if self.harden:
            # Rows are gone at this point; the bytes may not be. Hardening runs
            # after the sweep so the freed pages it rebuilds are the ones this
            # erasure created.
            self.harden_databases()
        if self.durable:
            # A rewrite is not durable until the device confirms it. Without
            # this the receipt describes the page cache, not the disk.
            fsync_paths(list(self.sqlite_paths()))
        return receipt

    def residue(self, request_id: str) -> ResidueReport:
        """What is still extractable, after the fact.

        Two numbers, deliberately not one. ``native_hits`` is what this
        system's own recall still serves; ``residual_hits`` is what survives
        in the stores when a reader is handed everything directly. A system
        that reports zero native hits but non-zero residual hits has not
        forgotten anything -- it has merely got lucky with its retriever.
        """
        receipt = self.log.find(request_id) if self.log is not None else None
        predicate = receipt.predicate if receipt else None
        report = ResidueReport(
            request_id=str(request_id),
            stores_scanned=self.covered_stores,
        )
        if predicate is None:
            return report
        for store in self.stores:
            for row_id in store.survivors(predicate):
                report.residual_hits.append("%s:%s" % (store.name, row_id))
        for store in self.stores:
            for row_id in store.native_hits(predicate):
                report.native_hits.append("%s:%s" % (store.name, row_id))
        report.native_hits = sorted(set(report.native_hits))
        report.residual_hits = sorted(set(report.residual_hits))
        return report

    def verify(self, receipt: ForgetReceipt) -> Dict[str, Any]:
        """Independent check that a receipt's claim still holds."""
        report = self.residue(receipt.request_id)
        return {
            "receipt_id": receipt.receipt_id,
            "complete": receipt.complete,
            "uncovered": list(receipt.uncovered),
            "removed": receipt.removed,
            "residue": report.to_dict(),
            "forgotten": report.clean,
        }


def sweep(root: Any, phrase: str, **kwargs: Any) -> Dict[str, Any]:
    """One-call helper: build a predicate, erase, report the residue."""
    forger = root if isinstance(root, Forger) else Forger(**kwargs)
    predicate = build_predicate(
        phrase,
        require_all=bool(kwargs.get("require_all", False)),
        extra_tokens=kwargs.get("extra_tokens") or (),
    )
    receipt = forger.forget(
        predicate,
        actor=str(kwargs.get("actor") or ""),
        reason=str(kwargs.get("reason") or REASON_USER_REQUEST),
        request_id=str(kwargs.get("request_id") or ""),
    )
    return forger.verify(receipt)


__all__ = [
    "CipherCapability",
    "ERASED_BODY",
    "ERASED_MARKER",
    "ERASURE_TABLE",
    "ForgetError",
    "ForgetReceipt",
    "Forger",
    "Predicate",
    "REASONS",
    "REASON_LEGAL_REQUEST",
    "REASON_RETENTION",
    "REASON_USER_REQUEST",
    "ReceiptLog",
    "ResidueReport",
    "SCHEMA_VERSION",
    "STORES",
    "StoreResult",
    "build_predicate",
    "canonical",
    "cipher_capability",
    "content_digest",
    "fsync_paths",
    "harden_sqlite",
    "normalize",
    "scan_raw_bytes",
    "scrub_sidecars",
    "sqlite_sidecars",
    "sweep",
]
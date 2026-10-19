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

STORES = (STORE_MEMORY, STORE_OBSERVATIONS, STORE_SUMMARIES, STORE_GRAPH, STORE_LESSONS)

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
    for token in extra_tokens:
        token = str(token or "").strip()
        if token and token not in raw_tokens:
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
        receipt_path: str = "",
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        self.clock = clock or time.time
        self.stores: List[_Store] = []
        if memory is not None:
            self.stores.extend(
                [_MemoryStore(memory), _ObservationStore(memory), _SummaryStore(memory)]
            )
        if graph is not None:
            self.stores.append(_GraphStore(graph))
        if lesson_journal is not None:
            self.stores.append(_LessonStore(lesson_journal))
        self.log = ReceiptLog(receipt_path) if receipt_path else None

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
    "content_digest",
    "normalize",
    "sweep",
]
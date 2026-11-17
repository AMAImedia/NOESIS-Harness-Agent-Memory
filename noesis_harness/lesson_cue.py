"""noesis_harness/lesson_cue.py

Cue-addressed lessons: what a past task learned, and the situation that makes
it fire again.

Patterns borrowed from:
- Harness2 (Google, Apache-2.0, arXiv 2610.14224) ``core/library.py`` --
  the ``EXPERIENCE.md`` lesson triple: a *cue* (the situation), a *lesson*
  (the transferable behaviour), and *evidence* (why we believe it). Their
  lesson is rejected unless all three are present; so is ours.
- Harness2 ``core/selection.py::_distil`` -- an extracted lesson must be
  evidence-supported before it may be stored, never merely plausible.
- agentmemory procedural tier + NOESIS ``procedures.py`` -- the "when <trigger>
  then <action>" overlap trigger, widened here into a multi-tier cue match.
- LoopX event fingerprints -- content-addressed idempotency on every write.

Clean-room: no Harness2 code was copied; only the data contract was ported.

This module is the missing closed loop in NOESIS. ``learning_promotion`` can
promote a *skill version* under human approval, but before this module there
was no data type for "a learned lesson that a later task recalls by its cue",
and therefore no path from a finished task to durable general knowledge.

Governance invariants (these differ from Harness2 and are deliberate):
- A lesson is born CANDIDATE. Only an explicit ``promote`` with a non-empty
  approver makes it ACTIVE. ``recall`` returns ACTIVE lessons by default.
- Storage is an append-only JSONL journal. Nothing is ever rewritten or
  deleted; a correction is a new record that supersedes an older one.
- Deterministic core: matching, scoring and ranking are pure functions of the
  inputs. Extraction of a lesson from a task is a pluggable callback, so the
  core never calls an LLM.
- Stdlib only.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from dataclasses import dataclass, replace
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from .inverted_index import STOPWORDS
    from .resource_lineage import SENSITIVITIES
    from .text_norm import tokenize
except ImportError:  # pragma: no cover - direct script import
    from noesis_harness.inverted_index import STOPWORDS
    from noesis_harness.resource_lineage import SENSITIVITIES
    from noesis_harness.text_norm import tokenize


def meaningful_tokens(text: str) -> Tuple[str, ...]:
    """Tokenize for cue matching, dropping words that carry no signal.

    A cue is written in prose -- "the ledger totals do not reconcile" -- so
    without this the exact tier is unreachable: "the", "do" and "not" would
    have to appear in the future context for the cue to match itself. The
    stopword set is the one ``inverted_index`` already uses, so the whole
    project tokenizes one way; tokens shorter than three characters go too,
    which is the same cutoff ``procedures.py`` applies and which is what keeps
    ordinary verbs like "do" and "is" out of a cue's identity.
    """
    return tuple(
        token for token in tokenize(text) if token not in STOPWORDS and len(token) >= 3
    )


SCHEMA_VERSION = "noesis.lesson-cue.v1"

# Typed statuses, not scattered booleans.
STATUS_CANDIDATE = "candidate"
STATUS_ACTIVE = "active"
STATUS_SUPERSEDED = "superseded"
STATUS_RETIRED = "retired"

STATUSES = (STATUS_CANDIDATE, STATUS_ACTIVE, STATUS_SUPERSEDED, STATUS_RETIRED)

DEFAULT_MAX_ITEMS = 12
DEFAULT_MAX_CHARS = 12000
DEFAULT_MIN_SCORE = 0.34

#: Tier weights, highest precedence first. Mirrors the ``retrieval_ladder``
#: ordering so a cue can be reached by a prefix or a fuzzy match, not only by
#: an exact word overlap.
_TIER_WEIGHTS = {
    "exact": 1.00,
    "prefix": 0.85,
    "substring": 0.70,
    "fuzzy": 0.55,
    "overlap": 0.45,
}

#: Weight of the lesson's own confidence inside the final cue score. The rest
#: is the match tier. Both are bounded, so the score stays in ``[0, 1]``.
_CONFIDENCE_WEIGHT = 0.30

_FUZZY_MAX_DISTANCE = 2


class LessonCueError(ValueError):
    """Raised when a lesson or a lesson request is malformed."""


class LessonJournalConflict(LessonCueError):
    """Raised when one lesson_id carries two different records."""


# --------------------------------------------------------------------------
# records
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Lesson:
    """One evidence-supported lesson addressed by a cue.

    ``cue`` is the situation, phrased so that a future context can be compared
    against it. ``lesson`` is the transferable behaviour. ``evidence`` states
    why we believe it and must name something checkable -- a task id, a run id,
    a measurement. ``confidence`` is the author's belief in ``[0, 1]`` and is
    never a substitute for ``evidence``: a lesson with no evidence string is
    rejected at construction, exactly as Harness2 rejects a lesson missing any
    of cue/lesson/evidence.
    """

    lesson_id: str
    cue: str
    lesson: str
    evidence: str
    domain: str
    confidence: float = 0.5
    scope: str = "local"
    sensitivity: str = "internal"
    source_ids: Tuple[str, ...] = ()
    status: str = STATUS_CANDIDATE
    created_at: float = 0.0
    provenance_digest: str = ""
    supersedes: str = ""

    def __post_init__(self) -> None:
        _validate(self)

    # -- identity ----------------------------------------------------------

    @property
    def fingerprint(self) -> str:
        """Content digest over the lesson's meaning, not its identity.

        Two lessons with the same cue, lesson, evidence and domain are the same
        lesson however many times they were recorded. This is what makes the
        write path idempotent.
        """
        payload = "|".join(
            [
                self.domain.strip().casefold(),
                self.cue.strip().casefold(),
                self.lesson.strip().casefold(),
                self.evidence.strip().casefold(),
                "%.4f" % self.confidence,
            ]
        )
        return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @property
    def digest(self) -> str:
        """Full-record digest, used for tamper evidence in the journal."""
        return "sha256:" + hashlib.sha256(
            canonical(self.to_dict()).encode("utf-8")
        ).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lesson_id": self.lesson_id,
            "cue": self.cue,
            "lesson": self.lesson,
            "evidence": self.evidence,
            "domain": self.domain,
            "confidence": self.confidence,
            "scope": self.scope,
            "sensitivity": self.sensitivity,
            "source_ids": list(self.source_ids),
            "status": self.status,
            "created_at": self.created_at,
            "provenance_digest": self.provenance_digest,
            "supersedes": self.supersedes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Lesson":
        return cls(
            lesson_id=str(data.get("lesson_id") or ""),
            cue=str(data.get("cue") or ""),
            lesson=str(data.get("lesson") or ""),
            evidence=str(data.get("evidence") or ""),
            domain=str(data.get("domain") or ""),
            confidence=float(data.get("confidence") or 0.0),
            scope=str(data.get("scope") or "local"),
            sensitivity=str(data.get("sensitivity") or "internal"),
            source_ids=tuple(data.get("source_ids") or ()),
            status=str(data.get("status") or STATUS_CANDIDATE),
            created_at=float(data.get("created_at") or 0.0),
            provenance_digest=str(data.get("provenance_digest") or ""),
            supersedes=str(data.get("supersedes") or ""),
        )

    # -- convenience -------------------------------------------------------

    @property
    def cue_tokens(self) -> frozenset:
        return frozenset(meaningful_tokens(self.cue))

    def size_chars(self) -> int:
        return len(self.cue) + len(self.lesson) + len(self.evidence)


@dataclass(frozen=True)
class LessonRecord:
    """One journal line: a lesson plus the decision taken about it."""

    entry_id: str
    action: str
    lesson: Lesson
    actor: str
    reason: str
    at: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "entry_id": self.entry_id,
            "action": self.action,
            "lesson": self.lesson.to_dict(),
            "actor": self.actor,
            "reason": self.reason,
            "at": self.at,
            "digest": self.lesson.digest,
        }


@dataclass(frozen=True)
class CueMatch:
    """A scored cue hit with the reason it scored as it did."""

    lesson: Lesson
    score: float
    tier: str
    reason: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lesson_id": self.lesson.lesson_id,
            "score": round(self.score, 6),
            "tier": self.tier,
            "cue": self.lesson.cue,
            "domain": self.lesson.domain,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class CueDecision:
    """The bounded, auditable outcome of a cue lookup."""

    selected: Tuple[CueMatch, ...]
    excluded: Tuple[Tuple[str, str], ...]
    used_chars: int
    max_chars: int
    digest: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected": [m.to_dict() for m in self.selected],
            "excluded": [list(pair) for pair in self.excluded],
            "used_chars": self.used_chars,
            "max_chars": self.max_chars,
            "digest": self.digest,
        }

    def as_prompt_lines(self) -> List[str]:
        """Render the decision as the block a context builder would inject.

        Deterministic and budget-bounded: the caller decides where it goes, and
        this never writes anywhere.
        """
        lines: List[str] = []
        for match in self.selected:
            lines.append(
                "- [cue] %s\n  [lesson] %s\n  [evidence] %s\n  [confidence] %.2f"
                % (
                    match.lesson.cue,
                    match.lesson.lesson,
                    match.lesson.evidence,
                    match.lesson.confidence,
                )
            )
        return lines


# --------------------------------------------------------------------------
# cue matching
# --------------------------------------------------------------------------


def _levenshtein(a: str, b: str, max_distance: int) -> int:
    """Damerau-Levenshtein with an early exit beyond ``max_distance``."""
    la, lb = len(a), len(b)
    if abs(la - lb) > max_distance:
        return max_distance + 1
    prev2: List[int] = []
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        row_min = cur[0]
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                cur[j] = min(cur[j], prev2[j - 2] + 1)
            row_min = min(row_min, cur[j])
        if row_min > max_distance:
            return max_distance + 1
        prev2, prev = prev, cur
    return prev[lb]


def match_tier(query_tokens: Sequence[str], cue: Lesson) -> Tuple[str, Dict[str, Any]]:
    """The single best tier a cue is reachable by, and why.

    Tiers are disjoint and checked in precedence order, so a cue that matches
    exactly is never also reported as a fuzzy match. The tier name is the
    explanation: a reader can tell a genuine hit from a stretch.
    """
    cue_tokens = cue.cue_tokens
    if not query_tokens or not cue_tokens:
        return "none", {"reason": "empty_cue_or_query"}

    qset = set(query_tokens)
    if cue_tokens <= qset:
        return "exact", {"reason": "all_cue_tokens_present", "matched": sorted(cue_tokens)}

    for token in sorted(cue_tokens):
        for candidate in sorted(qset):
            if len(candidate) > len(token) and candidate.startswith(token):
                return "prefix", {"reason": "query_token_extends_cue_token", "token": token}

    for token in sorted(cue_tokens):
        for candidate in sorted(qset):
            if len(candidate) < len(token) and token in candidate:
                return "substring", {"reason": "cue_token_inside_query_token", "token": token}

    best: Optional[Tuple[int, str]] = None
    for token in sorted(cue_tokens):
        if len(token) < 5:
            continue
        for candidate in sorted(qset):
            if abs(len(candidate) - len(token)) > _FUZZY_MAX_DISTANCE:
                continue
            distance = _levenshtein(token, candidate, _FUZZY_MAX_DISTANCE)
            # Distance 0 is not a fuzzy hit: it is a shared token, and
            # reporting it here would make the fuzzy tier reachable by an
            # exact match and hide the real state of the cue. It is handled
            # by the overlap tier below, keeping the tiers disjoint.
            if 1 <= distance <= _FUZZY_MAX_DISTANCE and (best is None or distance < best[0]):
                best = (distance, token)
    if best is not None:
        return "fuzzy", {"reason": "edit_distance_within_tolerance", "token": best[1], "distance": best[0]}

    shared = cue_tokens & qset
    if shared:
        overlap = len(shared) / float(len(cue_tokens))
        return "overlap", {"reason": "partial_token_overlap", "overlap": round(overlap, 4)}

    return "none", {"reason": "no_shared_token"}


def cue_score(
    query_tokens: Sequence[str], cue: Lesson, *, confidence_weight: float = _CONFIDENCE_WEIGHT
) -> Tuple[float, str, Dict[str, Any]]:
    """Score one cue against a context, in ``[0, 1]``, with its tier and reason.

    The score is ``(1 - confidence_weight) * tier + confidence_weight *
    confidence``. It is a pure function: same cue, same context, same score,
    on every machine and every run.
    """
    tier, reason = match_tier(query_tokens, cue)
    if tier == "none":
        return 0.0, tier, reason
    weight = float(confidence_weight)
    if not 0.0 <= weight <= 1.0:
        raise LessonCueError("confidence_weight_must_be_between_zero_and_one")
    score = (1.0 - weight) * _TIER_WEIGHTS[tier] + weight * max(0.0, min(1.0, cue.confidence))
    return max(0.0, min(1.0, score)), tier, reason


# --------------------------------------------------------------------------
# selection
# --------------------------------------------------------------------------


def _validate(lesson: Lesson) -> None:
    if not str(lesson.lesson_id).strip():
        raise LessonCueError("lesson_id_required")
    for field_name in ("cue", "lesson", "evidence", "domain"):
        if not str(getattr(lesson, field_name)).strip():
            raise LessonCueError("%s_required" % field_name)
    if not isinstance(lesson.confidence, (int, float)) or isinstance(lesson.confidence, bool):
        raise LessonCueError("confidence_must_be_numeric")
    if not 0.0 <= float(lesson.confidence) <= 1.0:
        raise LessonCueError("confidence_must_be_between_zero_and_one")
    if lesson.status not in STATUSES:
        raise LessonCueError("unknown_status")
    if not str(lesson.scope).strip():
        raise LessonCueError("scope_required")
    if lesson.sensitivity not in SENSITIVITIES:
        raise LessonCueError("unknown_sensitivity")
    for source in lesson.source_ids:
        if not isinstance(source, str) or not source.strip():
            raise LessonCueError("source_ids_invalid")


class CueSelector:
    """Recall lessons by cue, bounded, scoped, deny-by-default, deterministic."""

    def __init__(
        self,
        *,
        max_items: int = DEFAULT_MAX_ITEMS,
        max_chars: int = DEFAULT_MAX_CHARS,
        min_score: float = DEFAULT_MIN_SCORE,
        allowed_scopes: Sequence[str] = ("local",),
        allowed_sensitivities: Sequence[str] = ("public", "internal"),
        allowed_domains: Sequence[str] = (),
        require_active: bool = True,
        confidence_weight: float = _CONFIDENCE_WEIGHT,
    ) -> None:
        self.max_items = int(max_items)
        self.max_chars = int(max_chars)
        self.min_score = float(min_score)
        self.allowed_scopes = frozenset(allowed_scopes)
        self.allowed_sensitivities = frozenset(allowed_sensitivities)
        self.allowed_domains = frozenset(d.lower() for d in allowed_domains)
        self.require_active = bool(require_active)
        self.confidence_weight = float(confidence_weight)

    def select(
        self, lessons: Iterable[Lesson], context: str, *, limit: Optional[int] = None
    ) -> CueDecision:
        """Return the lessons whose cue matches ``context``, plus what was refused.

        Nothing is silently discarded: every rejection is returned with its
        cause, so an operator can tell a policy refusal from a budget refusal.
        Ordering is a total order -- score descending, then ``lesson_id``
        ascending -- so two runs over the same lessons return the same list.
        """
        if context is None or not str(context).strip():
            return CueDecision((), (), 0, self.max_chars, _decision_digest((), ()))
        tokens = meaningful_tokens(context)
        if not tokens:
            return CueDecision((), (), 0, self.max_chars, _decision_digest((), ()))

        cap = self.max_items if limit is None else min(self.max_items, int(limit))
        excluded: List[Tuple[str, str]] = []
        scored: List[CueMatch] = []
        seen_fingerprints: Dict[str, str] = {}

        for lesson in lessons:
            if lesson.status == STATUS_RETIRED:
                excluded.append((lesson.lesson_id, "retired"))
                continue
            if self.require_active and lesson.status != STATUS_ACTIVE:
                excluded.append((lesson.lesson_id, "not_active"))
                continue
            if self.allowed_scopes and lesson.scope not in self.allowed_scopes:
                excluded.append((lesson.lesson_id, "scope_denied"))
                continue
            if self.allowed_sensitivities and lesson.sensitivity not in self.allowed_sensitivities:
                excluded.append((lesson.lesson_id, "sensitivity_denied"))
                continue
            if self.allowed_domains and lesson.domain.strip().casefold() not in self.allowed_domains:
                excluded.append((lesson.lesson_id, "domain_denied"))
                continue
            fingerprint = lesson.fingerprint
            if fingerprint in seen_fingerprints:
                excluded.append((lesson.lesson_id, "duplicate_of:" + seen_fingerprints[fingerprint]))
                continue

            score, tier, reason = cue_score(
                tokens, lesson, confidence_weight=self.confidence_weight
            )
            if score < self.min_score:
                excluded.append((lesson.lesson_id, "below_min_score"))
                continue
            if len(scored) >= cap:
                excluded.append((lesson.lesson_id, "item_budget"))
                continue
            seen_fingerprints[fingerprint] = lesson.lesson_id
            scored.append(CueMatch(lesson=lesson, score=score, tier=tier, reason=reason))

        scored.sort(key=lambda m: (-m.score, m.lesson.lesson_id))

        selected: List[CueMatch] = []
        used = 0
        for match in scored:
            size = match.lesson.size_chars()
            if used + size > self.max_chars:
                excluded.append((match.lesson.lesson_id, "char_budget"))
                continue
            used += size
            selected.append(match)

        return CueDecision(
            selected=tuple(selected),
            excluded=tuple(sorted(excluded)),
            used_chars=used,
            max_chars=self.max_chars,
            digest=_decision_digest(selected, excluded),
        )


# --------------------------------------------------------------------------
# append-only journal
# --------------------------------------------------------------------------


def canonical(payload: Any) -> str:
    """Deterministic JSON: sorted keys, no incidental whitespace."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _decision_digest(selected: Sequence[CueMatch], excluded: Sequence[Tuple[str, str]]) -> str:
    body = {
        "selected": [[m.lesson.lesson_id, round(m.score, 6), m.tier] for m in selected],
        "excluded": [list(pair) for pair in excluded],
    }
    return "sha256:" + hashlib.sha256(canonical(body).encode("utf-8")).hexdigest()


class LessonJournal:
    """Append-only JSONL record of lesson decisions.

    Every write is idempotent by fingerprint: re-recording the same lesson is a
    no-op, and the same ``lesson_id`` with different content is a conflict
    rather than a silent overwrite. Nothing is ever mutated or deleted.
    """

    def __init__(self, path: str, *, clock: Optional[Callable[[], float]] = None) -> None:
        self.path = str(path)
        self.clock = clock or time.time

    # -- reading -----------------------------------------------------------

    def replay(self) -> List[LessonRecord]:
        """Every record ever written, in order. A truncated tail is skipped."""
        records: List[LessonRecord] = []
        try:
            handle = open(self.path, "r", encoding="utf-8")
        except OSError:
            return records
        with handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                    records.append(
                        LessonRecord(
                            entry_id=str(payload["entry_id"]),
                            action=str(payload["action"]),
                            lesson=Lesson.from_dict(payload["lesson"]),
                            actor=str(payload.get("actor") or ""),
                            reason=str(payload.get("reason") or ""),
                            at=float(payload.get("at") or 0.0),
                        )
                    )
                except (ValueError, KeyError, TypeError):
                    continue
        return records

    def current(self) -> Dict[str, Lesson]:
        """The last known state of every lesson, keyed by ``lesson_id``.

        This is a replay projection, never a mutation of the log: a later
        record for the same id replaces the earlier one in the projection only.
        """
        state: Dict[str, Lesson] = {}
        for record in self.replay():
            state[record.lesson.lesson_id] = record.lesson
        return state

    def lessons(
        self,
        *,
        status: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> List[Lesson]:
        """Lessons in deterministic order: ``created_at`` then ``lesson_id``."""
        out = [
            lesson
            for lesson in self.current().values()
            if (status is None or lesson.status == status)
            and (domain is None or lesson.domain.strip().casefold() == domain.strip().casefold())
        ]
        out.sort(key=lambda lesson: (lesson.created_at, lesson.lesson_id))
        return out

    # -- writing -----------------------------------------------------------

    def record(
        self,
        lesson: Lesson,
        action: str,
        *,
        actor: str = "",
        reason: str = "",
        at: Optional[float] = None,
    ) -> str:
        """Append one decision. Returns the ``entry_id``, which is content-addressed.

        Raises ``LessonJournalConflict`` when this ``lesson_id`` already exists
        with different content -- the caller must supersede explicitly instead.
        """
        if not lesson.lesson_id:
            raise LessonCueError("lesson_id_required")
        fingerprint = lesson.fingerprint
        for record in self.replay():
            if record.lesson.lesson_id != lesson.lesson_id:
                continue
            if record.lesson.fingerprint == fingerprint and record.action == action:
                return record.entry_id  # idempotent re-record: a no-op, not a duplicate
            if record.action == "record" and record.lesson.fingerprint != fingerprint:
                raise LessonJournalConflict(
                    "lesson_id %s already records different content; append a lesson that "
                    "supersedes it instead of rewriting history" % lesson.lesson_id
                )
        stamp = float(at) if at is not None else float(self.clock())
        stamped = replace(lesson, created_at=stamp)
        entry_id = "les_" + hashlib.sha256(
            canonical([action, stamped.to_dict(), actor, reason]).encode("utf-8")
        ).hexdigest()[:24]
        record = LessonRecord(
            entry_id=entry_id,
            action=action,
            lesson=stamped,
            actor=str(actor or ""),
            reason=str(reason or ""),
            at=stamp,
        )
        line = canonical(record.to_dict())
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        return entry_id

    def promote(
        self,
        lesson_id: str,
        *,
        actor: str,
        reason: str = "",
        at: Optional[float] = None,
    ) -> Lesson:
        """Make a CANDIDATE lesson ACTIVE. Explicit and attributable, never automatic.

        There is no code path in this module that promotes a lesson without an
        actor. That is the governance boundary NOESIS holds and Harness2 does
        not: their reflection step writes straight into the library.
        """
        if not str(actor).strip():
            raise LessonCueError("approver_identity_required")
        current = self.current()
        lesson = current.get(lesson_id)
        if lesson is None:
            raise KeyError(lesson_id)
        if lesson.status == STATUS_ACTIVE:
            return lesson  # idempotent: already active
        if lesson.status == STATUS_RETIRED:
            raise LessonCueError("cannot_promote_a_retired_lesson")
        stamp = float(at) if at is not None else float(self.clock())
        promoted = replace(lesson, status=STATUS_ACTIVE, created_at=stamp)
        self.record(promoted, "promote", actor=actor, reason=reason, at=stamp)
        return promoted

    def supersede(
        self,
        old_lesson_id: str,
        replacement: Lesson,
        *,
        actor: str,
        reason: str = "",
        at: Optional[float] = None,
    ) -> str:
        """Retire one lesson by appending its successor. History is preserved."""
        if not str(actor).strip():
            raise LessonCueError("approver_identity_required")
        current = self.current()
        if old_lesson_id not in current:
            raise KeyError(old_lesson_id)
        stamp = float(at) if at is not None else float(self.clock())
        self.record(
            replace(current[old_lesson_id], status=STATUS_SUPERSEDED),
            "supersede",
            actor=actor,
            reason=reason,
            at=stamp,
        )
        return self.record(
            replace(replacement, status=STATUS_ACTIVE, supersedes=old_lesson_id, created_at=stamp),
            "supersede",
            actor=actor,
            reason=reason,
            at=stamp,
        )

    def retire(
        self, lesson_id: str, *, actor: str, reason: str = "", at: Optional[float] = None
    ) -> Lesson:
        """Stop offering a lesson. Append-only: the earlier records stay."""
        if not str(actor).strip():
            raise LessonCueError("approver_identity_required")
        current = self.current()
        lesson = current.get(lesson_id)
        if lesson is None:
            raise KeyError(lesson_id)
        if lesson.status == STATUS_RETIRED:
            return lesson
        stamp = float(at) if at is not None else float(self.clock())
        retired = replace(lesson, status=STATUS_RETIRED, created_at=stamp)
        self.record(retired, "retire", actor=actor, reason=reason, at=stamp)
        return retired

    def summary(self) -> Dict[str, Any]:
        """Counts and a digest of the whole log, for evidence reports."""
        records = self.replay()
        counts: Dict[str, int] = {}
        for record in records:
            counts[record.action] = counts.get(record.action, 0) + 1
        stamps = [record.at for record in records] or [0.0]
        return {
            "schema_version": SCHEMA_VERSION,
            "total_records": len(records),
            "counts": counts,
            "earliest_at": min(stamps),
            "latest_at": max(stamps),
            "log_digest": "sha256:"
            + hashlib.sha256(
                canonical([record.entry_id for record in records]).encode("utf-8")
            ).hexdigest(),
        }


# --------------------------------------------------------------------------
# extraction (pluggable, never in the deterministic core)
# --------------------------------------------------------------------------

Extractor = Callable[[Dict[str, Any]], Optional[Dict[str, str]]]


def build_lesson(
    fields: Dict[str, str],
    *,
    lesson_id: str = "",
    confidence: float = 0.5,
    scope: str = "local",
    sensitivity: str = "internal",
    source_ids: Sequence[str] = (),
    provenance_digest: str = "",
    at: Optional[float] = None,
) -> Lesson:
    """Build a validated CANDIDATE lesson from cue/lesson/evidence strings.

    A no-op convenience around the constructor. The lesson stays a candidate
    until someone promotes it; nothing here decides that.
    """
    return Lesson(
        lesson_id=str(lesson_id or ("les_" + uuid.uuid4().hex[:16])),
        cue=str(fields.get("cue") or "").strip(),
        lesson=str(fields.get("lesson") or "").strip(),
        evidence=str(fields.get("evidence") or "").strip(),
        domain=str(fields.get("domain") or "").strip(),
        confidence=float(confidence),
        scope=str(scope),
        sensitivity=str(sensitivity),
        source_ids=tuple(source_ids),
        status=STATUS_CANDIDATE,
        created_at=float(at) if at is not None else 0.0,
        provenance_digest=str(provenance_digest or ""),
    )


def extract_lesson(task: Dict[str, Any], extractor: Optional[Extractor]) -> Optional[Lesson]:
    """Run a caller-supplied extractor over a finished task record.

    With no extractor this returns ``None``: the deterministic core refuses to
    invent a lesson, which is what keeps this module free of any LLM
    dependency. A caller that does supply one (an LLM, a rule set, a human)
    gets the same validation and the same governance as every other path.
    """
    if extractor is None or not isinstance(task, dict):
        return None
    fields = extractor(task)
    if not isinstance(fields, dict):
        return None
    if not all(str(fields.get(key) or "").strip() for key in ("cue", "lesson", "evidence")):
        return None
    return build_lesson(
        fields,
        lesson_id=str(task.get("lesson_id") or fields.get("lesson_id") or ""),
        confidence=float(fields.get("confidence") or 0.5),
        scope=str(task.get("scope") or "local"),
        sensitivity=str(task.get("sensitivity") or "internal"),
        source_ids=tuple(task.get("source_ids") or ()),
        provenance_digest=str(task.get("provenance_digest") or ""),
    )


_WS_RE = re.compile(r"\s+")


def normalize_domain(domain: str) -> str:
    """Canonical form of a domain label: whitespace-collapsed and casefolded."""
    return _WS_RE.sub(" ", str(domain or "")).strip().casefold()


__all__ = [
    "CueDecision",
    "CueMatch",
    "CueSelector",
    "Lesson",
    "LessonCueError",
    "LessonJournal",
    "LessonJournalConflict",
    "LessonRecord",
    "SCHEMA_VERSION",
    "STATUS_ACTIVE",
    "STATUS_CANDIDATE",
    "STATUS_RETIRED",
    "STATUS_SUPERSEDED",
    "STATUSES",
    "build_lesson",
    "canonical",
    "cue_score",
    "extract_lesson",
    "match_tier",
    "meaningful_tokens",
    "normalize_domain",
]
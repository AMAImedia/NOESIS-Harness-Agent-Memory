"""noesis_harness/blind_select.py

Anonymised selection between candidate artifacts, plus the machine-readable
contrast between what was chosen and what it replaced.

Patterns borrowed from:
- Harness2 (Google, Apache-2.0, arXiv 2610.14224) ``core/selection.py`` --
  ``assign_ids`` sorts labels canonically and then shuffles under a seed
  derived from ``sha1(task_id|k|mode)``, so the mapping is stable across reruns
  and carries no positional bias; ``_anon_id`` walks A..Z, AA..AZ; the
  ``id_map`` is written to ``selection.json`` so the reasoning can be
  de-anonymised after the fact; and a chooser failure falls back to a neutral
  stand-in and never raises.
- Harness2 ``core/context.py::_write_pool`` -- a ``harness.diff`` per candidate
  computed with ``difflib.unified_diff`` against the reference, so a chooser
  reads what changed rather than being told.
- NOESIS ``evidence.py`` -- conflict handling by explicit proposal rather than
  silent replacement, which is how a dropped candidate is reported here.

Clean-room: no Harness2 code was copied; only the method was ported.

Governance invariants (deliberately stricter than Harness2):

- A blind selection is a *proposal*. This module never promotes, never
  activates, never writes into a memory. It returns a record; what happens
  next is the caller's decision through ``promotion_integration``.
- A chooser is a caller-supplied callback. With no chooser, or on any chooser
  failure, selection falls back to a deterministic neutral rule rather than
  raising: a failed judgement is not a result.
- Nothing is discarded silently. Every candidate that did not enter the pool
  is reported with the cause.
"""

from __future__ import annotations

import difflib
import hashlib
import random
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple, Union

try:
    from .lesson_cue import canonical
except ImportError:  # pragma: no cover - direct script import
    from noesis_harness.lesson_cue import canonical


SCHEMA_VERSION = "noesis.blind-select.v1"

DEFAULT_SALT = "noesis.blind-select.v1"

_CHOICE_RE = re.compile(r"```choice\s*\n?\s*([A-Za-z0-9_\-]+)\s*\n?\s*```", re.S)
_WHY_RE = re.compile(r"<why>(.*?)</why>", re.S)

Chooser = Callable[["SelectionTask"], Tuple[str, str]]


class BlindSelectError(ValueError):
    """Raised when a selection task or its output is malformed."""


def anonym_id(index: int) -> str:
    """A..Z, AA..AZ, BA... -- always accepted by the choice parser."""
    out = ""
    n = int(index) + 1
    while n:
        n, rem = divmod(n - 1, 26)
        out = chr(ord("A") + rem) + out
    return out


def assign_ids(labels: Sequence[str], *, salt: str = DEFAULT_SALT) -> Dict[str, str]:
    """Map anon id -> label: canonical sort, then a seeded shuffle.

    The shuffle seed is derived from the salt alone, so the same candidate set
    always produces the same mapping -- a rerun is comparable -- while the
    original position of a candidate carries no information into the id.
    Duplicate labels are refused rather than collapsed: two candidates sharing
    a label could not be told apart in the result.
    """
    ordered = [str(label) for label in labels]
    if len(set(ordered)) != len(ordered):
        raise BlindSelectError("candidate_labels_must_be_unique")
    unique = sorted(ordered)
    if not unique:
        raise BlindSelectError("at_least_one_candidate_required")
    seed = int(hashlib.sha256(str(salt).encode("utf-8")).hexdigest()[:12], 16)
    shuffled = list(unique)
    random.Random(seed).shuffle(shuffled)
    return {anonym_id(i): label for i, label in enumerate(shuffled)}


def reverse_ids(id_map: Mapping[str, str]) -> Dict[str, str]:
    """The inverse mapping, so stored reasoning can be de-anonymised later."""
    return {label: anon for anon, label in id_map.items()}


# --------------------------------------------------------------------------
# candidates
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Candidate:
    """One artifact offered for adoption.

    ``body`` is the readable content the chooser compares. ``files`` are
    auxiliary artifacts copied alongside it -- named explicitly by the caller,
    never discovered by scanning a run directory, because a scan would also
    carry whatever else that directory holds.
    """

    label: str
    body: str
    files: Tuple[Tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not str(self.label).strip():
            raise BlindSelectError("candidate_label_required")
        if not isinstance(self.body, str):
            raise BlindSelectError("candidate_body_must_be_text")

    @property
    def is_answer(self) -> bool:
        return bool(self.body.strip())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "body_chars": len(self.body),
            "body_lines": self.body.count("\n") + 1,
            "files": [name for name, _ in self.files],
        }


@dataclass(frozen=True)
class SelectionTask:
    """What the chooser is given: the candidates, anonymised, plus the reference."""

    task_id: str
    prompt: str
    id_map: Dict[str, str]
    reference: Mapping[str, str] = field(default_factory=dict)

    def anon_labels(self) -> List[str]:
        return sorted(self.id_map)

    def resolve(self, anon: str) -> str:
        if anon not in self.id_map:
            raise BlindSelectError("anon_id_not_in_pool: %r" % anon)
        return self.id_map[anon]

    def de_anonymize(self, text: str) -> str:
        """Rewrite anon ids in stored reasoning back to real labels.

        Longest id first, so ``AA`` is not corrupted by the ``A`` that starts
        it. Used when reading a past selection back, never before the choice.
        """
        if not text:
            return text
        out = str(text)
        for anon in sorted(self.id_map, key=len, reverse=True):
            out = re.sub(r"\b%s\b" % re.escape(anon), self.id_map[anon], out)
        return out


@dataclass(frozen=True)
class Contrast:
    """What the chosen candidate changed relative to the reference.

    This is the textual "before -> after" artifact. A number such as a recall
    gain says an outcome moved; this says *what* moved, which is the part a
    later task can actually reuse.
    """

    chosen_label: str
    reference_label: str
    added: Tuple[str, ...] = ()
    removed: Tuple[str, ...] = ()
    modified: Tuple[str, ...] = ()
    char_delta: int = 0
    diff: str = ""

    @property
    def changed(self) -> bool:
        return bool(self.added or self.removed or self.modified)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chosen_label": self.chosen_label,
            "reference_label": self.reference_label,
            "added": list(self.added),
            "removed": list(self.removed),
            "modified": list(self.modified),
            "char_delta": self.char_delta,
            "changed": self.changed,
            "diff_sha256": "sha256:"
            + hashlib.sha256(self.diff.encode("utf-8")).hexdigest(),
        }


@dataclass(frozen=True)
class Selection:
    """The outcome: one chosen artifact, or an honest refusal to choose."""

    task_id: str
    chosen_id: str
    chosen_label: str
    ok: bool
    why: str = ""
    id_map: Dict[str, str] = field(default_factory=dict)
    dropped: Tuple[Tuple[str, str], ...] = ()
    n_candidates: int = 0
    fallback: bool = False
    trivial: bool = False
    error: str = ""
    contrast: Optional[Contrast] = None
    salt: str = DEFAULT_SALT

    @property
    def is_adopted(self) -> bool:
        """Whether a real chooser picked this, as opposed to a fallback.

        A caller feeding this into a promotion pipeline should require
        ``is_adopted`` rather than ``ok``: a neutral fallback is a non-answer,
        and promoting it would be a silent policy bypass.
        """
        return self.ok and not self.fallback and not self.trivial

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "task_id": self.task_id,
            "chosen_id": self.chosen_id,
            "chosen_label": self.chosen_label,
            "ok": self.ok,
            "is_adopted": self.is_adopted,
            "why": self.why,
            "id_map": dict(self.id_map),
            "dropped": [list(pair) for pair in self.dropped],
            "n_candidates": self.n_candidates,
            "fallback": self.fallback,
            "trivial": self.trivial,
            "error": self.error,
            "salt": self.salt,
            "contrast": self.contrast.to_dict() if self.contrast else None,
            "digest": "sha256:"
            + hashlib.sha256(
                canonical(
                    {
                        "task_id": self.task_id,
                        "chosen_label": self.chosen_label,
                        "id_map": dict(self.id_map),
                        "n_candidates": self.n_candidates,
                    }
                ).encode("utf-8")
            ).hexdigest(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Selection":
        return cls(
            task_id=str(data.get("task_id") or ""),
            chosen_id=str(data.get("chosen_id") or ""),
            chosen_label=str(data.get("chosen_label") or ""),
            ok=bool(data.get("ok")),
            why=str(data.get("why") or ""),
            id_map=dict(data.get("id_map") or {}),
            dropped=tuple(tuple(p) for p in (data.get("dropped") or ())),
            n_candidates=int(data.get("n_candidates") or 0),
            fallback=bool(data.get("fallback")),
            trivial=bool(data.get("trivial")),
            error=str(data.get("error") or ""),
            salt=str(data.get("salt") or DEFAULT_SALT),
        )


# --------------------------------------------------------------------------
# contrast
# --------------------------------------------------------------------------


def build_contrast(
    chosen: Candidate, reference: Optional[Candidate] = None
) -> Contrast:
    """The textual difference between the chosen artifact and a reference.

    With no reference the contrast is empty rather than "everything is new",
    so an absent baseline can never be misread as a large improvement.
    """
    if reference is None:
        return Contrast(
            chosen_label=chosen.label,
            reference_label="",
            added=tuple(sorted(name for name, _ in chosen.files)),
            char_delta=len(chosen.body),
        )
    chosen_names = {name for name, _ in chosen.files}
    reference_names = {name for name, _ in reference.files}
    added = tuple(sorted(chosen_names - reference_names))
    removed = tuple(sorted(reference_names - chosen_names))
    lines: List[str] = []
    if chosen.body != reference.body:
        lines.extend(
            difflib.unified_diff(
                reference.body.splitlines(keepends=True),
                chosen.body.splitlines(keepends=True),
                fromfile="reference/%s" % reference.label,
                tofile="chosen/%s" % chosen.label,
            )
        )
    for name in sorted(reference_names | chosen_names):
        before = dict(reference.files).get(name)
        after = dict(chosen.files).get(name)
        if before == after:
            continue
        lines.extend(
            difflib.unified_diff(
                (before or "").splitlines(keepends=True),
                (after or "").splitlines(keepends=True),
                fromfile="reference/%s" % name,
                tofile="chosen/%s" % name,
            )
        )
    return Contrast(
        chosen_label=chosen.label,
        reference_label=reference.label,
        added=added,
        removed=removed,
        char_delta=len(chosen.body) - len(reference.body),
        diff="".join(lines),
    )


# --------------------------------------------------------------------------
# pool rendering
# --------------------------------------------------------------------------


def render_pool(candidates: Sequence[Candidate]) -> Tuple[List[Candidate], List[Tuple[str, str]]]:
    """Keep only the candidates that produced an answer; report every drop."""
    kept: List[Candidate] = []
    dropped: List[Tuple[str, str]] = []
    for candidate in candidates:
        if not candidate.is_answer:
            dropped.append((candidate.label, "no_artifact"))
            continue
        kept.append(candidate)
    return kept, dropped


def write_candidates(
    dest: Union[Path, str],
    selection: Selection,
    candidates: Sequence[Candidate],
    task: SelectionTask,
) -> int:
    """Write one anonymised, untrimmed file per candidate. Returns files written.

    The body is written whole. Nothing is trimmed to fit a prompt: a chooser
    that reads a trimmed artifact is choosing on the trimming, not on the work.
    """
    root = Path(dest)
    root.mkdir(parents=True, exist_ok=True)
    by_label = {candidate.label: candidate for candidate in candidates}
    written = 0
    for anon in sorted(task.id_map):
        candidate = by_label.get(task.id_map[anon])
        if candidate is None:
            continue
        header = (
            "<!-- candidate %s: %d chars, %d lines. COMPLETE -- nothing trimmed. -->\n"
            % (anon, len(candidate.body), candidate.body.count("\n") + 1)
        )
        (root / ("%s.md" % anon)).write_text(header + candidate.body, encoding="utf-8")
        written += 1
        if candidate.files:
            files_dir = root / anon
            files_dir.mkdir(parents=True, exist_ok=True)
            for name, body in candidate.files:
                (files_dir / name).write_text(body, encoding="utf-8")
                written += 1
    (root / "id_map.json").write_text(canonical(dict(task.id_map)), encoding="utf-8")
    (root / "selection.json").write_text(canonical(selection.to_dict()), encoding="utf-8")
    return written


# --------------------------------------------------------------------------
# selection
# --------------------------------------------------------------------------


def parse_choice(reply: str) -> Tuple[str, str]:
    """Pull ``(anon_id, why)`` out of a chooser's reply.

    Raises :class:`BlindSelectError` on anything malformed, which the caller
    treats as a chooser failure and not as a result.
    """
    match = _CHOICE_RE.search(reply or "")
    if not match:
        raise BlindSelectError("no_choice_block")
    why_match = _WHY_RE.search(reply or "")
    return match.group(1).strip(), (why_match.group(1).strip() if why_match else "")


def _fallback(id_map: Mapping[str, str], reason: str) -> Tuple[str, str]:
    """The neutral stand-in after a chooser failure: the base, else the first.

    Deterministic and explicable. It marks the selection ``fallback`` so a
    promotion pipeline can refuse it rather than mistake it for a judgement.
    """
    base = sorted(str(label) for label in id_map.values() if str(label).startswith("base"))
    target = base[0] if base else sorted(id_map.values())[0]
    for anon, label in id_map.items():
        if label == target:
            return anon, reason
    return sorted(id_map)[0], reason


def run_selection(
    task_id: str,
    candidates: Sequence[Candidate],
    *,
    prompt: str = "",
    chooser: Optional[Chooser] = None,
    salt: str = DEFAULT_SALT,
    reference: Optional[Candidate] = None,
    work_dir: Optional[str] = None,
) -> Selection:
    """Choose one artifact from an anonymised pool.

    Failure policy, deliberately: a chooser that raises, returns something
    unparseable, or names an id that is not in the pool is a *chooser
    failure*. That falls back to a neutral deterministic choice and is flagged
    ``fallback=True`` -- it never raises and it never scores as a judgement.
    A malformed caller argument still raises, because that is a bug rather than
    an outcome.
    """
    if not str(task_id).strip():
        raise BlindSelectError("task_id_required")
    if not candidates:
        raise BlindSelectError("at_least_one_candidate_required")

    kept, dropped = render_pool(candidates)
    if not kept:
        return Selection(
            task_id=task_id,
            chosen_id="",
            chosen_label="",
            ok=False,
            dropped=tuple(dropped),
            n_candidates=0,
            error="no_candidate_produced_an_artifact",
            salt=salt,
        )

    id_map = assign_ids([candidate.label for candidate in kept], salt=salt + "|" + task_id)
    task = SelectionTask(task_id=task_id, prompt=prompt, id_map=id_map, reference=dict(reference.files) if reference else {})

    chosen_id = ""
    why = ""
    fallback = False
    error = ""

    if chooser is not None:
        try:
            chosen_id, why = chooser(task)
            if chosen_id not in id_map:
                raise BlindSelectError("chose %r, which is not one of %s" % (chosen_id, ", ".join(sorted(id_map))))
        except BlindSelectError as exc:
            error = str(exc)
            chosen_id, why = _fallback(id_map, error)
            fallback = True
        except Exception as exc:  # a chooser that blows up is a failure, not a crash
            error = "%s: %s" % (type(exc).__name__, exc)
            chosen_id, why = _fallback(id_map, error)
            fallback = True
    else:
        chosen_id, why = _fallback(id_map, "no_chooser_supplied")
        fallback = True

    chosen_label = id_map[chosen_id]
    chosen = next(candidate for candidate in kept if candidate.label == chosen_label)

    selection = Selection(
        task_id=task_id,
        chosen_id=chosen_id,
        chosen_label=chosen_label,
        ok=True,
        why=task.de_anonymize(why) if why else "",
        id_map=dict(id_map),
        dropped=tuple(dropped),
        n_candidates=len(kept),
        fallback=fallback,
        error=error[:400],
        contrast=build_contrast(chosen, reference),
        salt=salt,
    )
    if work_dir:
        write_candidates(Path(work_dir) / task_id, selection, kept, task)
    return selection


def trivial_selection(
    task_id: str, candidate: Candidate, *, salt: str = DEFAULT_SALT
) -> Selection:
    """Adopt a single candidate without running a chooser at all.

    Used when only one artifact exists. ``trivial=True`` and
    ``is_adopted`` is False, so a pipeline cannot mistake a one-candidate run
    for a comparative decision.
    """
    if not candidate.is_answer:
        return Selection(
            task_id=task_id,
            chosen_id="",
            chosen_label="",
            ok=False,
            n_candidates=0,
            error="candidate_produced_no_artifact",
            salt=salt,
        )
    id_map = {"A": candidate.label}
    return Selection(
        task_id=task_id,
        chosen_id="A",
        chosen_label=candidate.label,
        ok=True,
        why="single candidate: no comparative choice was made",
        id_map=id_map,
        n_candidates=1,
        trivial=True,
        contrast=build_contrast(candidate),
        salt=salt,
    )


def parse_reply(reply: str) -> Tuple[str, str]:
    """Public alias of the reply parser, for callers that drive the chooser."""
    return parse_choice(reply)


def copy_evidence(src: Union[Path, str], dest: Union[Path, str]) -> int:
    """Copy a reference tree for a chooser to read, skipping compiled files."""
    source, target = Path(src), Path(dest)
    if not source.is_dir():
        return 0
    shutil.copytree(source, target, dirs_exist_ok=True)
    return sum(
        1
        for path in target.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )


__all__ = [
    "BlindSelectError",
    "Candidate",
    "Contrast",
    "SCHEMA_VERSION",
    "Selection",
    "SelectionTask",
    "anonym_id",
    "assign_ids",
    "build_contrast",
    "copy_evidence",
    "parse_choice",
    "parse_reply",
    "render_pool",
    "reverse_ids",
    "run_selection",
    "trivial_selection",
    "write_candidates",
]
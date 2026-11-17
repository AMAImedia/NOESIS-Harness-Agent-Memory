"""Bounded, provenance-aware reuse of successful agent experiences.

This module is a read-only selector. It never writes memory, executes skill/tool
content, or treats a high score as permission to cross scope or sensitivity.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable, Mapping, Tuple

from .resource_lineage import SENSITIVITIES


@dataclass(frozen=True)
class ExperienceRecord:
    experience_id: str
    content: str
    scope: str = "local"
    sensitivity: str = "internal"
    source_ids: Tuple[str, ...] = ()
    success_score: float = 0.0
    recency_score: float = 0.0
    provenance_digest: str = ""
    reusable: bool = True


@dataclass(frozen=True)
class ReuseDecision:
    selected: Tuple[ExperienceRecord, ...]
    excluded: Tuple[Tuple[str, str], ...]
    used_chars: int
    max_chars: int
    digest: str


class ExperienceReuseError(ValueError):
    """Raised when reuse policy or an experience record is malformed."""


def _score(record: ExperienceRecord) -> float:
    return 0.7 * max(0.0, min(1.0, record.success_score)) + 0.3 * max(0.0, min(1.0, record.recency_score))


def _validate(record: ExperienceRecord) -> None:
    if not record.experience_id or not record.content or not record.scope:
        raise ExperienceReuseError("experience_identity_required")
    if record.sensitivity not in SENSITIVITIES:
        raise ExperienceReuseError("unknown_sensitivity")
    if not 0.0 <= record.success_score <= 1.0 or not 0.0 <= record.recency_score <= 1.0:
        raise ExperienceReuseError("scores_must_be_between_zero_and_one")
    if not record.provenance_digest.startswith("sha256:") or len(record.provenance_digest) != 71:
        raise ExperienceReuseError("provenance_digest_required")
    if any(not isinstance(source, str) or not source for source in record.source_ids):
        raise ExperienceReuseError("source_ids_invalid")


class ExperienceReuseSelector:
    """Select bounded experiences under explicit scope and sensitivity policy."""

    def __init__(self, max_chars: int = 12000, max_items: int = 32):
        if max_chars < 1 or max_items < 1:
            raise ValueError("reuse budgets must be positive")
        self.max_chars = max_chars
        self.max_items = max_items

    def select(
        self,
        records: Iterable[ExperienceRecord],
        *,
        allowed_scopes: Tuple[str, ...] = ("local",),
        allowed_sensitivities: Tuple[str, ...] = ("public", "internal"),
    ) -> ReuseDecision:
        if not allowed_scopes or any(not isinstance(scope, str) or not scope for scope in allowed_scopes):
            raise ValueError("allowed_scopes_invalid")
        if not set(allowed_sensitivities).issubset(SENSITIVITIES):
            raise ValueError("allowed_sensitivities_invalid")
        candidates = []
        excluded = []
        seen = set()
        for record in records:
            if record.experience_id in seen:
                excluded.append((record.experience_id, "duplicate_id"))
                continue
            seen.add(record.experience_id)
            try:
                _validate(record)
            except ExperienceReuseError as exc:
                excluded.append((record.experience_id or "<missing>", str(exc)))
                continue
            if not record.reusable:
                excluded.append((record.experience_id, "not_reusable"))
            elif record.scope not in set(allowed_scopes):
                excluded.append((record.experience_id, "scope_denied"))
            elif record.sensitivity not in set(allowed_sensitivities):
                excluded.append((record.experience_id, "sensitivity_denied"))
            else:
                candidates.append(record)
        candidates.sort(key=lambda item: (-_score(item), item.experience_id))
        selected = []
        used = 0
        for record in candidates:
            if len(selected) >= self.max_items:
                excluded.append((record.experience_id, "item_budget"))
                continue
            separator = 2 if selected else 0
            cost = len(record.content)
            if cost + separator > self.max_chars - used:
                excluded.append((record.experience_id, "char_budget"))
                continue
            selected.append(record)
            used += cost + separator
        rendered = "\n\n".join(record.content for record in selected)
        digest = "sha256:" + hashlib.sha256(rendered.encode("utf-8")).hexdigest()
        return ReuseDecision(tuple(selected), tuple(excluded), used, self.max_chars, digest)


__all__ = ["ExperienceRecord", "ExperienceReuseError", "ExperienceReuseSelector", "ReuseDecision"]

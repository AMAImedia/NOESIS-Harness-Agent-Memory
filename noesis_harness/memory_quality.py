"""Deterministic memory and long-context quality evidence."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence, Tuple


class MemoryQualityError(ValueError):
    pass


@dataclass(frozen=True)
class MemoryQualityCase:
    case_id: str
    relevant_source_ids: Tuple[str, ...]
    selected_source_ids: Tuple[str, ...]
    attributed_source_ids: Tuple[str, ...]
    conflict_resolution_correct: bool
    temporal_order_correct: bool
    retained_after_compaction_ids: Tuple[str, ...]
    required_after_compaction_ids: Tuple[str, ...]
    used_tokens: int
    budget_tokens: int
    leakage_free: bool = True

    def __post_init__(self) -> None:
        if not self.case_id or self.budget_tokens < 1 or self.used_tokens < 0:
            raise MemoryQualityError("case_and_budget_required")
        if not math.isfinite(float(self.used_tokens)):
            raise MemoryQualityError("used_tokens_invalid")


@dataclass(frozen=True)
class MemoryQualityOutcome:
    case_id: str
    recall: float
    attribution_precision: float
    conflict_resolution: float
    temporal_order: float
    compaction_retention: float
    budget_respected: bool
    leakage_free: bool


@dataclass(frozen=True)
class MemoryQualityMetrics:
    recall_mean: float
    attribution_precision_mean: float
    conflict_resolution_rate: float
    temporal_order_rate: float
    compaction_retention_mean: float
    budget_compliance_rate: float
    leakage_free_rate: float
    quality_score: float
    cases: int


def _ratio(numerator: int, denominator: int) -> float:
    return 1.0 if denominator == 0 else float(numerator) / float(denominator)


class MemoryQualityEvaluator:
    """Evaluate recorded memory behavior without model-generated grading."""
    def evaluate_case(self, case: MemoryQualityCase) -> MemoryQualityOutcome:
        relevant = set(case.relevant_source_ids)
        selected = set(case.selected_source_ids)
        attributed = set(case.attributed_source_ids)
        required = set(case.required_after_compaction_ids)
        retained = set(case.retained_after_compaction_ids)
        recall = _ratio(len(relevant & selected), len(relevant))
        attribution_precision = _ratio(len(attributed & relevant), len(attributed))
        compaction_retention = _ratio(len(required & retained), len(required))
        return MemoryQualityOutcome(case.case_id, recall, attribution_precision, float(case.conflict_resolution_correct), float(case.temporal_order_correct), compaction_retention, case.used_tokens <= case.budget_tokens, bool(case.leakage_free))

    def evaluate(self, cases: Sequence[MemoryQualityCase]) -> tuple[MemoryQualityOutcome, ...]:
        if not cases:
            raise MemoryQualityError("cases_required")
        if len({case.case_id for case in cases}) != len(cases):
            raise MemoryQualityError("duplicate_case_id")
        return tuple(self.evaluate_case(case) for case in cases)

    def metrics(self, cases: Sequence[MemoryQualityCase]) -> MemoryQualityMetrics:
        outcomes = self.evaluate(cases)
        n = float(len(outcomes))
        means = lambda field: sum(float(getattr(outcome, field)) for outcome in outcomes) / n
        score = sum((outcome.recall + outcome.attribution_precision + outcome.conflict_resolution + outcome.temporal_order + outcome.compaction_retention + float(outcome.budget_respected) + float(outcome.leakage_free)) / 7.0 for outcome in outcomes) / n
        return MemoryQualityMetrics(means("recall"), means("attribution_precision"), means("conflict_resolution"), means("temporal_order"), means("compaction_retention"), sum(outcome.budget_respected for outcome in outcomes) / n, sum(outcome.leakage_free for outcome in outcomes) / n, score, len(outcomes))


__all__ = ["MemoryQualityError", "MemoryQualityCase", "MemoryQualityOutcome", "MemoryQualityMetrics", "MemoryQualityEvaluator"]

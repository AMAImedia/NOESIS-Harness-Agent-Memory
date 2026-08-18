"""Deterministic metrics for governed multi-agent work products."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


class WorkProductBenchmarkError(ValueError):
    pass


@dataclass(frozen=True)
class WorkProductOutcome:
    case_id: str
    correct: bool
    delivered: bool
    leakage_free: bool
    recovered: bool
    attempts: int = 1
    reviewer_time_seconds: float = 0.0
    review_approved: bool = True
    committed: bool = True

    def __post_init__(self) -> None:
        if not self.case_id:
            raise WorkProductBenchmarkError("case_id_required")
        if int(self.attempts) < 1 or int(self.attempts) > 4:
            raise WorkProductBenchmarkError("attempts_out_of_range")
        if not math.isfinite(float(self.reviewer_time_seconds)) or float(self.reviewer_time_seconds) < 0:
            raise WorkProductBenchmarkError("reviewer_time_invalid")


@dataclass(frozen=True)
class WorkProductMetrics:
    correctness_rate: float
    delivery_rate: float
    leakage_free_rate: float
    recovery_rate: float
    review_approval_rate: float
    commit_rate: float
    mean_reviewer_time_seconds: float
    retry_rate: float
    work_product_score: float
    cases: int


class WorkProductBenchmarkEvaluator:
    """Compute reproducible bounded metrics; no LLM grading or hidden reward."""
    def evaluate(self, outcomes: Sequence[WorkProductOutcome]) -> WorkProductMetrics:
        rows = tuple(outcomes)
        if not rows:
            raise WorkProductBenchmarkError("outcomes_required")
        ids = [row.case_id for row in rows]
        if len(set(ids)) != len(ids):
            raise WorkProductBenchmarkError("duplicate_case_id")
        n = float(len(rows))
        correctness = sum(row.correct for row in rows) / n
        delivery = sum(row.delivered for row in rows) / n
        leakage = sum(row.leakage_free for row in rows) / n
        recovery = sum(row.recovered for row in rows) / n
        review = sum(row.review_approved for row in rows) / n
        commits = sum(row.committed for row in rows) / n
        reviewer_time = sum(float(row.reviewer_time_seconds) for row in rows) / n
        retry_rate = sum(row.attempts > 1 for row in rows) / n
        score = (correctness + delivery + leakage + recovery + review + commits) / 6.0
        return WorkProductMetrics(correctness, delivery, leakage, recovery, review, commits, reviewer_time, retry_rate, score, len(rows))


__all__ = ["WorkProductBenchmarkError", "WorkProductOutcome", "WorkProductMetrics", "WorkProductBenchmarkEvaluator"]

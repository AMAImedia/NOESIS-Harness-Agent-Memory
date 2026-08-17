"""Deterministic long-horizon trajectory evaluation for NOESIS.

The evaluator separates three process dimensions inspired by arXiv:2608.13417:
C1 solution framing, C2 execution, and C3 feedback control. It consumes only
recorded checkpoint/verifier signals; it never asks an LLM to grade behavior.
Scores are diagnostic proxies for local experiments, not claims of benchmark
compatibility with the paper's exact implementation.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple


def _clip(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


@dataclass(frozen=True)
class TrajectoryCheckpoint:
    step: int
    score: float
    delivered: bool = True
    correct: bool = True
    build_errors: int = 0

    def __post_init__(self) -> None:
        if self.step < 0:
            raise ValueError("step must be non-negative")
        if not math.isfinite(float(self.score)):
            raise ValueError("score must be finite")
        if int(self.build_errors) < 0:
            raise ValueError("build_errors must be non-negative")


@dataclass(frozen=True)
class TrajectoryMetrics:
    c1_solution_framing: float
    c2_execution: float
    c3_feedback_control: float
    peak_score: float
    final_score: float
    peak_retention: float
    dip_count: int
    mean_dip_depth: float
    recovery_credit: float
    recovery_steps: float
    delivery_rate: float
    build_error_rate: float
    horizon: int

    @property
    def outcome(self) -> float:
        return self.final_score


class TrajectoryEvaluator:
    """Compute reproducible process metrics from verifier trajectory records."""

    def __init__(self, horizon: int | None = None):
        if horizon is not None and horizon < 1:
            raise ValueError("horizon must be positive")
        self.horizon = horizon

    @staticmethod
    def _ordered(checkpoints: Sequence[TrajectoryCheckpoint]) -> List[TrajectoryCheckpoint]:
        if not checkpoints:
            raise ValueError("at least one checkpoint is required")
        ordered = sorted(checkpoints, key=lambda item: item.step)
        if any(a.step == b.step for a, b in zip(ordered, ordered[1:])):
            raise ValueError("checkpoint steps must be unique")
        return ordered

    def evaluate(self, checkpoints: Sequence[TrajectoryCheckpoint]) -> TrajectoryMetrics:
        rows = self._ordered(checkpoints)
        horizon = self.horizon or max(1, rows[-1].step)
        scores = [_clip(row.score) for row in rows]
        running_best: List[float] = []
        current_best = 0.0
        for score in scores:
            current_best = max(current_best, score)
            running_best.append(current_best)
        peak = max(scores)
        final = scores[-1]

        # C1: area under the running-best curve. The initial state is carried
        # backward to step zero and the last value forward to the horizon.
        points = [(0, running_best[0])]
        points.extend((min(horizon, row.step), best) for row, best in zip(rows, running_best))
        points.append((horizon, running_best[-1]))
        area = 0.0
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            if x1 > x0:
                area += (x1 - x0) * (y0 + y1) / 2.0
        c1 = _clip(area / horizon)

        evaluated = rows[1:] if len(rows) > 1 else rows
        delivery_values = [1.0 if row.delivered and row.correct else 0.0 for row in evaluated]
        delivery_rate = sum(delivery_values) / len(delivery_values)
        build_error_rate = sum(1 for row in evaluated if row.build_errors > 0) / len(evaluated)
        execution_values = []
        for row, delivered in zip(evaluated, delivery_values):
            build_discount = 1.0 / (1.0 + min(10, row.build_errors) / 10.0)
            execution_values.append(delivered * (0.75 + 0.25 * build_discount))
        c2 = sum(execution_values) / len(execution_values)

        dips: List[Tuple[int, float, float]] = []
        best_before = scores[0]
        for index, score in enumerate(scores[1:], start=1):
            if score < best_before:
                dips.append((index, best_before, score))
            best_before = max(best_before, score)
        dip_count = len(dips)
        mean_dip_depth = (sum(before - score for _, before, score in dips) / dip_count) if dips else 0.0
        recovery_values: List[float] = []
        recovery_steps: List[float] = []
        for index, before, score in dips:
            future = scores[index:]
            recovered_index = next((offset for offset, candidate in enumerate(future) if candidate >= before), None)
            if recovered_index is None:
                recovery_values.append(0.0)
                recovery_steps.append(float(len(scores) - index))
            else:
                loss = max(1e-9, before - score)
                recovered = max(0.0, max(future[: recovered_index + 1]) - score)
                recovery_values.append(_clip(recovered / loss))
                recovery_steps.append(float(recovered_index))
        recovery_credit = sum(recovery_values) / len(recovery_values) if recovery_values else peak_retention(final, peak)
        mean_recovery_steps = sum(recovery_steps) / len(recovery_steps) if recovery_steps else 0.0
        retention = peak_retention(final, peak)
        c3 = _clip((retention + recovery_credit) / 2.0) if dips else retention

        return TrajectoryMetrics(
            c1_solution_framing=c1,
            c2_execution=_clip(c2),
            c3_feedback_control=c3,
            peak_score=peak,
            final_score=final,
            peak_retention=retention,
            dip_count=dip_count,
            mean_dip_depth=_clip(mean_dip_depth),
            recovery_credit=_clip(recovery_credit),
            recovery_steps=mean_recovery_steps,
            delivery_rate=_clip(delivery_rate),
            build_error_rate=_clip(build_error_rate),
            horizon=horizon,
        )


def peak_retention(final_score: float, peak_score: float) -> float:
    if peak_score <= 0.0:
        return 1.0 if final_score <= 0.0 else 0.0
    return _clip(final_score / peak_score)


__all__ = ["TrajectoryCheckpoint", "TrajectoryEvaluator", "TrajectoryMetrics", "peak_retention"]

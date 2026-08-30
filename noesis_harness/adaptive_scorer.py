"""noesis_harness/adaptive_scorer.py — outcome-fed adaptive scoring.

Patterns: LoopX adaptive score.
Stdlib only.
"""
from __future__ import annotations
from typing import Dict, List, Tuple

class AdaptiveScorer:
    def __init__(self, lr: float = 0.1, decay: float = 0.99):
        if not (0 < lr <= 1): raise ValueError("lr in (0,1]")
        if not (0 < decay <= 1): raise ValueError("decay in (0,1]")
        self._lr = lr; self._decay = decay
        self._w_success = 0.5; self._w_recency = 0.5; self._n = 0

    def score(self, success_score: float, recency_score: float) -> float:
        return self._w_success * max(0.0, min(1.0, success_score)) + \
               self._w_recency * max(0.0, min(1.0, recency_score))

    def update(self, success_score: float, recency_score: float, outcome: str) -> None:
        target = 1.0 if outcome == "success" else (0.5 if outcome == "partial" else 0.0)
        predicted = self.score(success_score, recency_score)
        error = target - predicted
        self._w_success = max(0.0, min(1.0, self._w_success + self._lr * error * success_score))
        self._w_recency = max(0.0, min(1.0, self._w_recency + self._lr * error * recency_score))
        # renormalize
        total = self._w_success + self._w_recency
        if total > 0:
            self._w_success /= total; self._w_recency /= total
        self._n += 1

    def weights(self) -> Tuple[float, float]: return (self._w_success, self._w_recency)
    def count(self) -> int: return self._n

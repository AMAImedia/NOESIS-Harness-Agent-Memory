"""noesis_harness/composite_score.py — layered weighted composite scoring.

Provenance: ported from the wshobson/agents repository
(``plugins/plugin-eval/src/plugin_eval/engine.py``: ``DIMENSION_WEIGHTS`` /
``LAYER_BLENDS`` / ``_assemble_composite`` / letter grades; and
``models.py`` confidence tiers). Reduced to a stdlib-only, deterministic
scorer with explicit confidence tiers.

Pattern: weighted mean -> per-layer blend renormalized over present layers
only (absent layers never drag the score down) -> bounded anti-pattern
penalty -> letter grade + confidence tier.

Stdlib only. Python 3.9 compatible.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, List, Optional, Tuple


class Confidence(str, Enum):
    """Evidence-confidence tier of a composite score."""

    ESTIMATED = "estimated"
    MEASURED = "measured"
    CERTIFIED = "certified"


class Layer(str, Enum):
    """Evaluation layer a signal belongs to."""

    STATIC = "static"
    JUDGE = "judge"
    SIMULATION = "simulation"


LAYER_BLENDS: Dict[Layer, float] = {
    Layer.STATIC: 0.4,
    Layer.JUDGE: 0.4,
    Layer.SIMULATION: 0.2,
}

_ANTI_PATTERN_FACTOR = 0.95


@dataclass(frozen=True)
class Signal:
    """A single weighted observation from one evaluation layer.

    ``score`` may be supplied outside [0, 1] and is clamped into range.
    ``weight`` must be non-negative (zero is allowed).
    """

    name: str
    layer: Layer
    score: float
    weight: float

    def __post_init__(self) -> None:
        if self.weight < 0.0:
            raise ValueError("signal weight must be non-negative")
        if self.score < 0.0:
            clamped = 0.0
        elif self.score > 1.0:
            clamped = 1.0
        else:
            clamped = float(self.score)
        object.__setattr__(self, "score", clamped)


@dataclass(frozen=True)
class Composite:
    """Immutable composite result over a set of signals."""

    score: float
    grade: str
    confidence: Confidence
    layers: Dict[str, float]
    applied_weight: float


def grade_for(score: float) -> str:
    """Map a 0..100 score to a letter grade."""
    if score >= 97.0:
        return "A+"
    if score >= 93.0:
        return "A"
    if score >= 80.0:
        return "B"
    if score >= 70.0:
        return "C"
    if score >= 60.0:
        return "D"
    return "F"


def confidence_from_layers(present: Iterable[Layer]) -> Confidence:
    """Derive the confidence tier from the set of present layers."""
    found = set(present)
    if {Layer.STATIC, Layer.JUDGE, Layer.SIMULATION} <= found:
        return Confidence.CERTIFIED
    if Layer.STATIC in found and Layer.JUDGE in found:
        return Confidence.MEASURED
    return Confidence.ESTIMATED


def score_composite(
    signals: List[Signal],
    anti_patterns: Optional[List[str]] = None,
) -> Composite:
    """Compute a layered weighted composite score.

    Raises ValueError when the total signal weight is not positive.
    Anti-pattern penalties are applied once per unique entry in sorted
    order, so the result is independent of input ordering.
    """
    total_weight = 0.0
    weighted_sum = 0.0
    layer_acc: Dict[Layer, Tuple[float, float]] = {}
    for signal in signals:
        total_weight += signal.weight
        weighted_sum += signal.score * signal.weight
        acc_sum, acc_weight = layer_acc.get(signal.layer, (0.0, 0.0))
        layer_acc[signal.layer] = (
            acc_sum + signal.score * signal.weight,
            acc_weight + signal.weight,
        )

    if total_weight <= 0.0:
        raise ValueError("total signal weight must be positive")

    layers: Dict[str, float] = {}
    blend_num = 0.0
    blend_den = 0.0
    for layer in Layer:
        acc_sum, acc_weight = layer_acc.get(layer, (0.0, 0.0))
        if acc_weight <= 0.0:
            continue
        layer_mean = acc_sum / acc_weight
        layers[layer.value] = layer_mean
        blend = LAYER_BLENDS[layer]
        blend_num += blend * layer_mean
        blend_den += blend

    blended = blend_num / blend_den if blend_den > 0.0 else 0.0
    score = round(100.0 * blended, 2)

    if anti_patterns:
        for _ in sorted(anti_patterns):
            score = max(0.0, score * _ANTI_PATTERN_FACTOR)

    return Composite(
        score=score,
        grade=grade_for(score),
        confidence=confidence_from_layers([s.layer for s in signals]),
        layers=layers,
        applied_weight=total_weight,
    )


__all__ = [
    "Confidence",
    "Layer",
    "LAYER_BLENDS",
    "Signal",
    "Composite",
    "score_composite",
    "confidence_from_layers",
    "grade_for",
]

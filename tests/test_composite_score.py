"""Tests for noesis_harness.composite_score (layered weighted scoring)."""
from __future__ import annotations

import unittest

from noesis_harness.composite_score import (
    LAYER_BLENDS,
    Composite,
    Confidence,
    Layer,
    Signal,
    confidence_from_layers,
    grade_for,
    score_composite,
)


def _static(score, weight=1.0, name="s"):
    return Signal(name=name, layer=Layer.STATIC, score=score, weight=weight)


class TestCompositeScore(unittest.TestCase):
    def test_single_signal_score(self):
        result = score_composite([_static(0.9)])
        self.assertEqual(result.score, 90.0)
        self.assertEqual(result.grade, "B")
        self.assertEqual(result.confidence, Confidence.ESTIMATED)

    def test_single_signal_perfect_score(self):
        result = score_composite([_static(1.0)])
        self.assertEqual(result.score, 100.0)
        self.assertEqual(result.grade, "A+")

    def test_weighting(self):
        signals = [_static(0.2, weight=1.0, name="a"), _static(0.8, weight=3.0, name="b")]
        result = score_composite(signals)
        self.assertEqual(result.score, 65.0)
        self.assertEqual(result.applied_weight, 4.0)

    def test_zero_total_weight_raises(self):
        signals = [_static(0.5, weight=0.0), _static(0.5, weight=0.0)]
        with self.assertRaises(ValueError):
            score_composite(signals)

    def test_empty_signals_raises(self):
        with self.assertRaises(ValueError):
            score_composite([])

    def test_negative_weight_raises(self):
        with self.assertRaises(ValueError):
            Signal(name="bad", layer=Layer.STATIC, score=0.5, weight=-1.0)

    def test_score_clamping_high(self):
        self.assertEqual(_static(5.0).score, 1.0)

    def test_score_clamping_low(self):
        self.assertEqual(_static(-2.0).score, 0.0)

    def test_clamping_affects_composite(self):
        result = score_composite([_static(3.0), _static(-3.0)])
        self.assertEqual(result.score, 50.0)

    def test_renormalization_when_layer_absent(self):
        signals = [
            Signal("a", Layer.STATIC, 0.8, 1.0),
            Signal("b", Layer.JUDGE, 0.6, 1.0),
        ]
        result = score_composite(signals)
        self.assertEqual(result.score, 70.0)
        self.assertNotIn(Layer.SIMULATION.value, result.layers)

    def test_layer_blend_weights(self):
        self.assertEqual(LAYER_BLENDS[Layer.STATIC], 0.4)
        self.assertEqual(LAYER_BLENDS[Layer.JUDGE], 0.4)
        self.assertEqual(LAYER_BLENDS[Layer.SIMULATION], 0.2)

    def test_layer_blend_keys(self):
        signals = [
            Signal("a", Layer.STATIC, 0.5, 1.0),
            Signal("b", Layer.JUDGE, 0.5, 1.0),
            Signal("c", Layer.SIMULATION, 0.5, 1.0),
        ]
        result = score_composite(signals)
        self.assertEqual(set(result.layers.keys()), {"static", "judge", "simulation"})
        self.assertEqual(result.score, 50.0)

    def test_layer_means(self):
        signals = [
            Signal("a", Layer.STATIC, 0.4, 1.0),
            Signal("b", Layer.STATIC, 0.6, 1.0),
            Signal("c", Layer.JUDGE, 1.0, 1.0),
        ]
        result = score_composite(signals)
        self.assertAlmostEqual(result.layers["static"], 0.5)
        self.assertAlmostEqual(result.layers["judge"], 1.0)

    def test_confidence_static_only_estimated(self):
        result = score_composite([_static(0.5)])
        self.assertEqual(result.confidence, Confidence.ESTIMATED)

    def test_confidence_static_judge_measured(self):
        signals = [Signal("a", Layer.STATIC, 0.5, 1.0), Signal("b", Layer.JUDGE, 0.5, 1.0)]
        result = score_composite(signals)
        self.assertEqual(result.confidence, Confidence.MEASURED)

    def test_confidence_all_layers_certified(self):
        signals = [
            Signal("a", Layer.STATIC, 0.5, 1.0),
            Signal("b", Layer.JUDGE, 0.5, 1.0),
            Signal("c", Layer.SIMULATION, 0.5, 1.0),
        ]
        result = score_composite(signals)
        self.assertEqual(result.confidence, Confidence.CERTIFIED)

    def test_confidence_from_layers_helper(self):
        self.assertEqual(confidence_from_layers([]), Confidence.ESTIMATED)
        self.assertEqual(confidence_from_layers([Layer.JUDGE]), Confidence.ESTIMATED)
        self.assertEqual(
            confidence_from_layers([Layer.STATIC, Layer.JUDGE]), Confidence.MEASURED
        )
        self.assertEqual(
            confidence_from_layers([Layer.STATIC, Layer.JUDGE, Layer.SIMULATION]),
            Confidence.CERTIFIED,
        )

    def test_anti_pattern_penalty_multiplicative(self):
        base = score_composite([_static(1.0)])
        penalized = score_composite([_static(1.0)], anti_patterns=["x", "y"])
        self.assertAlmostEqual(penalized.score, base.score * 0.95 * 0.95)
        self.assertAlmostEqual(penalized.score, 90.25)

    def test_anti_pattern_penalty_order_independent(self):
        a = score_composite([_static(0.8)], anti_patterns=["alpha", "beta", "gamma"])
        b = score_composite([_static(0.8)], anti_patterns=["gamma", "alpha", "beta"])
        self.assertEqual(a.score, b.score)

    def test_anti_pattern_penalty_floored_at_zero(self):
        result = score_composite([_static(0.0)], anti_patterns=["x"] * 50)
        self.assertEqual(result.score, 0.0)

    def test_no_anti_patterns_no_penalty(self):
        result = score_composite([_static(0.9)], anti_patterns=None)
        self.assertEqual(result.score, 90.0)

    def test_grade_boundaries(self):
        self.assertEqual(grade_for(97.0), "A+")
        self.assertEqual(grade_for(93.0), "A")
        self.assertEqual(grade_for(80.0), "B")
        self.assertEqual(grade_for(70.0), "C")
        self.assertEqual(grade_for(60.0), "D")
        self.assertEqual(grade_for(59.99), "F")
        self.assertEqual(grade_for(0.0), "F")

    def test_grade_boundaries_just_below(self):
        self.assertEqual(grade_for(96.99), "A")
        self.assertEqual(grade_for(92.99), "B")
        self.assertEqual(grade_for(79.99), "C")
        self.assertEqual(grade_for(69.99), "D")

    def test_composite_grade_matches_score(self):
        result = score_composite([_static(0.97)])
        self.assertEqual(result.score, 97.0)
        self.assertEqual(result.grade, "A+")

    def test_determinism_two_runs_equal(self):
        signals = [
            Signal("a", Layer.STATIC, 0.7, 2.0),
            Signal("b", Layer.JUDGE, 0.9, 1.0),
            Signal("c", Layer.SIMULATION, 0.3, 1.0),
        ]
        first = score_composite(signals, anti_patterns=["p", "q"])
        second = score_composite(signals, anti_patterns=["p", "q"])
        self.assertEqual(first.score, second.score)
        self.assertEqual(first.grade, second.grade)
        self.assertEqual(first.confidence, second.confidence)
        self.assertEqual(first.layers, second.layers)
        self.assertEqual(first.applied_weight, second.applied_weight)

    def test_composite_is_frozen(self):
        result = score_composite([_static(0.5)])
        self.assertIsInstance(result, Composite)
        with self.assertRaises(Exception):
            result.score = 1.0


if __name__ == "__main__":
    unittest.main()

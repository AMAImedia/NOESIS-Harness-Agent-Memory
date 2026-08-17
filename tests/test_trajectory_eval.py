import unittest

from noesis_harness.trajectory_eval import (
    TrajectoryCheckpoint,
    TrajectoryEvaluator,
    peak_retention,
)


class TrajectoryEvaluatorTests(unittest.TestCase):
    def test_early_progress_scores_solution_framing(self):
        early = TrajectoryEvaluator(horizon=10).evaluate([
            TrajectoryCheckpoint(0, 0.0),
            TrajectoryCheckpoint(1, 0.8),
            TrajectoryCheckpoint(10, 0.8),
        ])
        late = TrajectoryEvaluator(horizon=10).evaluate([
            TrajectoryCheckpoint(0, 0.0),
            TrajectoryCheckpoint(9, 0.8),
            TrajectoryCheckpoint(10, 0.8),
        ])
        self.assertGreater(early.c1_solution_framing, late.c1_solution_framing)

    def test_execution_penalizes_delivery_and_build_errors(self):
        metrics = TrajectoryEvaluator().evaluate([
            TrajectoryCheckpoint(0, 0.2),
            TrajectoryCheckpoint(1, 0.5, delivered=True, correct=True, build_errors=0),
            TrajectoryCheckpoint(2, 0.6, delivered=False, correct=False, build_errors=3),
        ])
        self.assertLess(metrics.c2_execution, 1.0)
        self.assertEqual(metrics.delivery_rate, 0.5)
        self.assertGreater(metrics.build_error_rate, 0.0)

    def test_feedback_control_detects_dip_and_recovery(self):
        metrics = TrajectoryEvaluator().evaluate([
            TrajectoryCheckpoint(0, 0.2),
            TrajectoryCheckpoint(1, 0.8),
            TrajectoryCheckpoint(2, 0.4),
            TrajectoryCheckpoint(3, 0.8),
        ])
        self.assertEqual(metrics.dip_count, 1)
        self.assertGreater(metrics.recovery_credit, 0.0)
        self.assertEqual(metrics.peak_retention, 1.0)
        self.assertEqual(metrics.final_score, 0.8)

    def test_unrecovered_regression_reduces_retention(self):
        metrics = TrajectoryEvaluator().evaluate([
            TrajectoryCheckpoint(0, 0.2),
            TrajectoryCheckpoint(1, 0.9),
            TrajectoryCheckpoint(2, 0.3),
        ])
        self.assertEqual(metrics.dip_count, 1)
        self.assertAlmostEqual(metrics.peak_retention, 1.0 / 3.0, places=6)
        self.assertLess(metrics.c3_feedback_control, 0.6)

    def test_invalid_trajectory_is_rejected(self):
        with self.assertRaises(ValueError):
            TrajectoryEvaluator().evaluate([])
        with self.assertRaises(ValueError):
            TrajectoryEvaluator().evaluate([
                TrajectoryCheckpoint(1, 0.2),
                TrajectoryCheckpoint(1, 0.3),
            ])
        with self.assertRaises(ValueError):
            TrajectoryEvaluator(0)

    def test_peak_retention_zero_peak_is_defined(self):
        self.assertEqual(peak_retention(0.0, 0.0), 1.0)
        self.assertEqual(peak_retention(0.2, 0.0), 0.0)


if __name__ == "__main__":
    unittest.main()

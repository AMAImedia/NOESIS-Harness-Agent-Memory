import unittest

from noesis_harness.work_product_benchmark import WorkProductBenchmarkError, WorkProductBenchmarkEvaluator, WorkProductOutcome


class WorkProductBenchmarkTests(unittest.TestCase):
    def test_metrics_are_deterministic_and_separate_quality_dimensions(self):
        outcomes = (
            WorkProductOutcome("case-a", True, True, True, False, attempts=1, reviewer_time_seconds=2.0),
            WorkProductOutcome("case-b", True, True, False, True, attempts=2, reviewer_time_seconds=4.0),
        )
        metrics = WorkProductBenchmarkEvaluator().evaluate(outcomes)
        self.assertEqual(metrics.cases, 2)
        self.assertEqual(metrics.correctness_rate, 1.0)
        self.assertEqual(metrics.delivery_rate, 1.0)
        self.assertEqual(metrics.leakage_free_rate, 0.5)
        self.assertEqual(metrics.recovery_rate, 0.5)
        self.assertEqual(metrics.mean_reviewer_time_seconds, 3.0)
        self.assertEqual(metrics.retry_rate, 0.5)
        self.assertLess(metrics.work_product_score, 1.0)

    def test_duplicate_and_invalid_outcomes_fail_closed(self):
        evaluator = WorkProductBenchmarkEvaluator()
        with self.assertRaisesRegex(WorkProductBenchmarkError, "duplicate_case_id"):
            evaluator.evaluate((WorkProductOutcome("same", True, True, True, True), WorkProductOutcome("same", True, True, True, True)))
        with self.assertRaisesRegex(WorkProductBenchmarkError, "attempts_out_of_range"):
            WorkProductOutcome("bad", True, True, True, True, attempts=5)


if __name__ == "__main__":
    unittest.main()

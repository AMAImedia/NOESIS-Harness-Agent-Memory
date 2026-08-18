import unittest

from noesis_harness.isolation_holdouts import ActiveDelegationLeakageSuite
from noesis_harness.memory_quality import MemoryQualityCase, MemoryQualityError, MemoryQualityEvaluator


class ActiveDelegationLeakageTests(unittest.TestCase):
    def test_concurrent_workspace_holdouts_all_pass(self):
        suite = ActiveDelegationLeakageSuite()
        results = suite.evaluate()
        self.assertEqual(tuple(result.case_id for result in results), suite.CASE_IDS)
        self.assertEqual(len(results), 4)
        self.assertTrue(all(result.passed for result in results), results)
        self.assertEqual(suite.pass_rate(), 1.0)


class MemoryQualityTests(unittest.TestCase):
    def test_quality_dimensions_are_separate_and_budget_is_hard(self):
        cases = (
            MemoryQualityCase("recall", ("s1", "s2"), ("s1",), ("s1",), True, True, ("s1",), ("s1", "s2"), 90, 100),
            MemoryQualityCase("conflict", ("s3",), ("s3", "noise"), ("noise",), False, True, ("s3",), ("s3",), 101, 100, leakage_free=False),
        )
        evaluator = MemoryQualityEvaluator()
        outcomes = evaluator.evaluate(cases)
        self.assertEqual(outcomes[0].recall, 0.5)
        self.assertEqual(outcomes[0].attribution_precision, 1.0)
        self.assertEqual(outcomes[0].compaction_retention, 0.5)
        self.assertTrue(outcomes[0].budget_respected)
        self.assertFalse(outcomes[1].budget_respected)
        metrics = evaluator.metrics(cases)
        self.assertEqual(metrics.cases, 2)
        self.assertEqual(metrics.budget_compliance_rate, 0.5)
        self.assertEqual(metrics.leakage_free_rate, 0.5)
        self.assertLess(metrics.quality_score, 1.0)

    def test_duplicate_and_empty_memory_cases_fail_closed(self):
        evaluator = MemoryQualityEvaluator()
        case = MemoryQualityCase("same", (), (), (), True, True, (), (), 0, 10)
        with self.assertRaisesRegex(MemoryQualityError, "duplicate_case_id"):
            evaluator.evaluate((case, case))
        with self.assertRaisesRegex(MemoryQualityError, "cases_required"):
            evaluator.metrics(())
        with self.assertRaisesRegex(MemoryQualityError, "case_and_budget_required"):
            MemoryQualityCase("", (), (), (), True, True, (), (), 0, 10)


if __name__ == "__main__":
    unittest.main()

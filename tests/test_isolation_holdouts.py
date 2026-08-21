import unittest

from noesis_harness.isolation_holdouts import ActiveDelegationLeakageSuite, CrossAgentLeakageSuite


class IsolationHoldoutTests(unittest.TestCase):
    def test_fixed_corpus_passes(self):
        suite = CrossAgentLeakageSuite()
        results = suite.evaluate()
        self.assertEqual(len(results), 12)
        self.assertTrue(all(result.passed for result in results), results)
        self.assertEqual(suite.pass_rate(), 1.0)

    def test_case_ids_are_stable(self):
        suite = CrossAgentLeakageSuite()
        self.assertEqual(tuple(result.case_id for result in suite.evaluate()), suite.CASE_IDS)

    def test_simultaneous_active_delegation_holdouts_pass(self):
        suite = ActiveDelegationLeakageSuite()
        results = suite.evaluate()
        self.assertEqual(len(results), 6)
        self.assertTrue(all(result.passed for result in results), results)
        self.assertEqual(suite.pass_rate(), 1.0)


if __name__ == "__main__":
    unittest.main()

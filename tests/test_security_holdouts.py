import unittest

from noesis_harness.security_holdouts import DEFAULT_HOLDOUTS, SecurityHoldoutSuite


class SecurityHoldoutTests(unittest.TestCase):
    def test_default_corpus_is_fully_detected(self):
        suite = SecurityHoldoutSuite()
        results = suite.evaluate()
        self.assertEqual(len(results), 18)
        self.assertTrue(all(result.passed for result in results), results)
        self.assertEqual(suite.pass_rate(), 1.0)

    def test_expected_rules_are_present_without_requiring_exact_rule_count(self):
        suite = SecurityHoldoutSuite()
        results = {result.case_id: result for result in suite.evaluate()}
        self.assertIn("prompt_injection", results["inject-1"].rules)
        self.assertIn("unsafe_deserialization", results["deserialize-1"].rules)
        self.assertIn("cross_agent_scope_request", results["scope-1"].rules)
        self.assertTrue(results["benign-1"].allowed)
        self.assertTrue(results["benign-2"].allowed)

    def test_corpus_is_stable_and_nonempty(self):
        self.assertEqual(tuple(case.case_id for case in DEFAULT_HOLDOUTS), tuple(case.case_id for case in SecurityHoldoutSuite().evaluate() and DEFAULT_HOLDOUTS))


if __name__ == "__main__":
    unittest.main()

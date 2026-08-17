import unittest

from noesis_harness.execution_assurance import AssuranceError, create_receipt, verify_receipt


class ExecutionAssuranceTests(unittest.TestCase):
    def test_receipt_is_deterministic_and_verifiable(self):
        kwargs = {"request": {"tool": "read"}, "policy": {"capability": "file.read"}, "workspace_before": "sha256:before", "workspace_after": "sha256:after", "outcome": "committed", "rollback_available": True, "side_effects": ("workspace_patch",)}
        first = create_receipt(**kwargs)
        second = create_receipt(**kwargs)
        self.assertEqual(first, second)
        self.assertTrue(verify_receipt(first))

    def test_tampering_is_detected(self):
        receipt = create_receipt(request={"x": 1}, policy={"allow": True}, workspace_before="sha256:b", workspace_after=None, outcome="failed", rollback_available=True)
        object.__setattr__(receipt, "outcome", "committed")
        self.assertFalse(verify_receipt(receipt))

    def test_invalid_outcome_fails_closed(self):
        with self.assertRaises(AssuranceError):
            create_receipt(request={}, policy={}, workspace_before="sha256:b", workspace_after=None, outcome="unknown", rollback_available=False)


if __name__ == "__main__":
    unittest.main()

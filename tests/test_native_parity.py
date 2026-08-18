import sys
import unittest

from noesis_harness.native_parity import operator_bundle, prepare_native_evidence


class NativeParityTests(unittest.TestCase):
    def test_linux_preparation_never_claims_native_pass(self):
        for target in ("windows", "macos"):
            evidence = prepare_native_evidence(target, current_platform="linux", python_version=(3, 14, 7))
            self.assertEqual(evidence.status, "not_run")
            self.assertFalse(evidence.execution_claim)
            self.assertEqual(evidence.reason, "target_host_or_python_mismatch")

    def test_matching_platform_still_requires_contract_execution(self):
        evidence = prepare_native_evidence("windows", current_platform="win32", python_version=(3, 14, 7))
        self.assertEqual(evidence.status, "not_run")
        self.assertFalse(evidence.execution_claim)
        self.assertEqual(evidence.reason, "parity_contract_not_executed")

    def test_operator_bundles_are_network_off_and_artifact_explicit(self):
        for target in ("windows", "macos"):
            bundle = operator_bundle(target)
            self.assertFalse(bundle["network_allowed"])
            self.assertFalse(bundle["credentials_required"])
            self.assertIn("environment.json", bundle["required_artifacts"])
            self.assertEqual(bundle["status_rule"], "not_run_is_not_passed")


if __name__ == "__main__":
    unittest.main()

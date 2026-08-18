import unittest

from scripts.build_cross_platform_gate_matrix import build


class CrossPlatformGateMatrixTests(unittest.TestCase):
    def native(self):
        return {
            "native_builds_executed": False,
            "network_allowed": False,
            "credentials_available": False,
            "results": [
                {"task_id": "portable-sha-sbom", "status": "passed"},
                {"task_id": "static-manifests", "status": "passed"},
                {"task_id": "python314-identity", "status": "passed"},
                {"task_id": "native-target-matrix", "status": "passed", "output": {"targets": {
                    "windows": {"evidence_status": "not_run", "reason": "target_host_or_python_mismatch"},
                    "macos": {"evidence_status": "not_run", "reason": "target_host_or_python_mismatch"},
                }}},
            ],
        }

    def external(self):
        return {"comparative_ready": False, "lanes": {
            "hermes": {"status": "not_run", "reason": "missing_exact_revision"},
            "opencode": {"status": "not_run", "reason": "missing_exact_revision"},
            "deepseek_harness": {"status": "not_run", "reason": "missing_exact_revision"},
        }}

    def test_local_pass_and_target_not_run_are_explicit(self):
        report = build(self.native(), self.external())
        self.assertEqual(report["overall_status"], "not_run")
        self.assertEqual(report["lanes"]["linux_local_verifier"]["status"], "passed")
        self.assertEqual(report["lanes"]["windows_native"]["status"], "not_run")
        self.assertFalse(report["native_or_external_execution_claim"])

    def test_invalid_status_is_fail_closed(self):
        external = self.external()
        external["lanes"]["hermes"]["status"] = "maybe"
        report = build(self.native(), external)
        self.assertEqual(report["overall_status"], "blocked")
        self.assertIn("hermes_external", report["invalid_status_lanes"])


if __name__ == "__main__":
    unittest.main()

import hashlib
import json
import unittest

from scripts.execution_conformance import build_conformance, verify_conformance


class ExecutionConformanceTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = {
            "native_host_status": "not_run",
            "external_lanes_status": "not_run",
            "claims": {"native_execution": False, "external_execution": False},
        }
        self.matrix = {"overall_status": "not_run", "comparative_ready": False}
        self.replay = {"status": "passed", "post_transfer_status": "passed", "release_gate_status": "passed"}
        self.gate = {"status": "passed"}

    def test_local_passed_native_and_external_not_run(self):
        report = build_conformance(self.snapshot, self.matrix, self.replay, self.gate)
        self.assertEqual(report["overall_status"], "not_run")
        self.assertEqual(report["execution_classes"]["local_replay"]["status"], "passed")
        self.assertEqual(report["execution_classes"]["native_host"]["status"], "not_run")
        self.assertEqual(verify_conformance(report)["status"], "passed")

    def test_external_passed_requires_matrix_and_claim(self):
        snapshot = dict(self.snapshot)
        snapshot["external_lanes_status"] = "passed"
        snapshot["claims"] = {"native_execution": False, "external_execution": True}
        report = build_conformance(snapshot, self.matrix, self.replay, self.gate)
        self.assertEqual(report["overall_status"], "blocked")
        self.assertIn("external_status_matrix_mismatch", report["reasons"])

    def test_native_passed_requires_claim(self):
        snapshot = dict(self.snapshot)
        snapshot["native_host_status"] = "passed"
        report = build_conformance(snapshot, self.matrix, self.replay, self.gate)
        self.assertEqual(report["overall_status"], "blocked")
        self.assertIn("native_status_claim_mismatch", report["reasons"])

    def test_tampering_is_blocked(self):
        report = build_conformance(self.snapshot, self.matrix, self.replay, self.gate)
        report["claims"]["worldwide_superiority"] = True
        self.assertEqual(verify_conformance(report)["reason"], "conformance_digest_mismatch")


if __name__ == "__main__":
    unittest.main()

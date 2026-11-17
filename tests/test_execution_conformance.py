import hashlib
import json
import unittest

from noesis_harness.execution_assurance import ExecutionBackend
from scripts.execution_conformance import (
    BackendVerificationHonestyError,
    build_backend_verification_section,
    build_conformance,
    verify_conformance,
)


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


class BackendVerificationSectionTests(unittest.TestCase):
    """Gate 3 parity: backend honesty surface projected in the conformance report."""

    def setUp(self):
        self.snapshot = {
            "native_host_status": "not_run",
            "external_lanes_status": "not_run",
            "claims": {"native_execution": False, "external_execution": False},
        }
        self.matrix = {"overall_status": "not_run", "comparative_ready": False}
        self.replay = {"status": "passed", "post_transfer_status": "passed", "release_gate_status": "passed"}
        self.gate = {"status": "passed"}

    def test_backend_verification_section_present_and_honest(self):
        report = build_conformance(self.snapshot, self.matrix, self.replay, self.gate)
        section = report["backend_verification"]
        self.assertEqual(section["status"], "passed")
        entries = {entry["backend"]: entry for entry in section["entries"]}
        self.assertEqual(
            set(entries),
            {"unconfigured_none", "failing_stub", "unavailable_stub"},
        )
        self.assertEqual(entries["unconfigured_none"]["status"], "not_run")
        self.assertEqual(entries["unconfigured_none"]["reason"], "backend_not_configured")
        self.assertEqual(entries["failing_stub"]["status"], "blocked")
        self.assertEqual(entries["unavailable_stub"]["status"], "unavailable")
        for entry in entries.values():
            self.assertNotEqual(entry["status"], "passed")
        self.assertEqual(verify_conformance(report)["status"], "passed")

    def test_backend_section_deterministic_across_builds(self):
        first = build_backend_verification_section()
        second = build_backend_verification_section()
        self.assertEqual(first, second)

    def test_mismatched_expectation_blocks_section(self):
        plan = (("unconfigured_none", None, "blocked", "backend_not_configured"),)
        section = build_backend_verification_section(plan)
        self.assertEqual(section["status"], "blocked")
        self.assertIn("unconfigured_none_honest_status_mismatch", section["reasons"])

    def test_unexpected_passed_entry_raises_fail_closed(self):
        class TamperedPassingBackend(ExecutionBackend):
            def verify_isolation(self):
                return {"status": "passed", "capabilities": ["namespace"]}

            def execute(self, request, policy):
                raise NotImplementedError

        plan = (("tampered_passing_stub", TamperedPassingBackend("tampered"), "blocked", "isolation_verification_refused"),)
        with self.assertRaises(BackendVerificationHonestyError):
            build_backend_verification_section(plan)


if __name__ == "__main__":
    unittest.main()

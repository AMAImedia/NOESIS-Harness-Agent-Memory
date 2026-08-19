import tempfile
import unittest
from pathlib import Path

from scripts.external_evidence_readiness import build_operator_preflight


class ExternalLanePreflightTests(unittest.TestCase):
    def test_missing_pins_are_not_run_and_never_executed(self):
        report = build_operator_preflight({"revisions": {}, "executables": {}, "workspace": "/tmp/operator"})
        self.assertEqual(report["status"], "not_run")
        self.assertFalse(report["execution_allowed"])
        self.assertFalse(report["automatic_execution"])
        self.assertTrue(any("missing_exact_revision" in item for item in report["checks"]))

    def test_complete_local_paths_are_only_ready_for_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "runner"
            executable.write_text("placeholder", encoding="utf-8")
            manifest = {"revisions": {lane: "rev-1" for lane in ("hermes", "opencode", "deepseek_harness")}, "executables": {lane: str(executable) for lane in ("hermes", "opencode", "deepseek_harness")}, "workspace": directory, "network_allowed": False, "credentials_present": False, "disposable_workspace": True}
            report = build_operator_preflight(manifest)
            self.assertEqual(report["status"], "ready_for_operator_approval")
            self.assertFalse(report["execution_allowed"])
            self.assertTrue(report["operator_approval_required"])

    def test_unsafe_policy_is_not_run(self):
        report = build_operator_preflight({"revisions": {lane: "rev" for lane in ("hermes", "opencode", "deepseek_harness")}, "executables": {}, "workspace": "/tmp/x", "network_allowed": True, "credentials_present": True, "disposable_workspace": False})
        self.assertEqual(report["status"], "not_run")
        self.assertIn("network_not_deny_by_default", report["checks"])
        self.assertIn("credentials_present", report["checks"])


if __name__ == "__main__":
    unittest.main()

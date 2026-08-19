import tempfile
import unittest

from scripts.build_native_replay_report import build_report


class NativeReplayReportTests(unittest.TestCase):
    def test_linux_host_is_not_run_and_never_claims_native_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            report = build_report("windows", directory, current_platform="linux", python_version=(3, 14, 7))
            self.assertEqual(report["status"], "not_run")
            self.assertFalse(report["artifact_replay_allowed"])
            self.assertFalse(report["native_execution_claim"])
            self.assertFalse(report["execution_performed"])

    def test_matching_host_with_missing_artifacts_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            report = build_report("macos", directory, current_platform="darwin", python_version=(3, 14, 7))
            self.assertEqual(report["status"], "blocked")
            self.assertFalse(report["artifact_replay_allowed"])
            self.assertFalse(report["external_execution_claim"])


if __name__ == "__main__":
    unittest.main()

"""Tests for the bounded recovery discovery runner.

Patterns are adapted from NOESIS bounded execution evidence and unittest
subprocess isolation; these tests avoid treating timeout as success.
"""
from __future__ import annotations

import sys
import unittest
from unittest.mock import patch

from scripts.run_recovery_discovery import _run_case, run


class RecoveryDiscoveryTests(unittest.TestCase):
    def test_run_known_fast_module_reports_passed(self):
        report = run("tests.test_release_audit_offline", timeout_seconds=10.0)
        self.assertEqual(report["schema_version"], "noesis.recovery-discovery.v1")
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["counts"]["failed"], 0)
        self.assertEqual(report["counts"]["timed_out"], 0)
        self.assertGreater(report["test_count"], 0)

    def test_timeout_is_incomplete_not_success(self):
        result = _run_case("tests.test_release_audit_offline.ReleaseAuditOfflineTests.test_offline_mode_never_calls_ls_remote", 0.0001)
        self.assertEqual(result["status"], "timed_out")
        self.assertIsNone(result["returncode"])

    def test_invalid_timeout_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "timeout_seconds_out_of_bounds"):
            run("tests.test_release_audit_offline", timeout_seconds=0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

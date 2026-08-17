from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from scripts.external_runner_contract import make_spec
from scripts.pinned_runner_adapter import RunnerConfigurationError, RunnerExecutionDenied, execute, prepare


class PinnedRunnerAdapterTests(unittest.TestCase):
    def spec(self, argv):
        return make_spec("hermes", "pinned-revision", argv, "a" * 64)

    def test_default_deny_requires_explicit_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RunnerExecutionDenied):
                prepare(self.spec([sys.executable, "-c", "print('safe')"]), directory)

    def test_approved_execution_uses_argv_and_minimal_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            outcome = execute(self.spec([sys.executable, "-c", "import os; print(os.getenv('NOESIS_EXTERNAL_RUNNER'))"]), directory, approval=True)
            self.assertEqual(outcome.status, "passed")
            self.assertEqual(outcome.returncode, 0)
            self.assertEqual(outcome.stdout.strip(), "1")
            self.assertFalse(outcome.timed_out)

    def test_workspace_policy_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            spec = dict(self.spec([sys.executable, "-c", "print('x')"]))
            spec["workspace"] = {"mode": "shared", "outside_access": "allow", "credentials": "present"}
            with self.assertRaises(RunnerConfigurationError):
                prepare(spec, directory, approval=True)

    def test_timeout_is_reported_without_exception_leak(self):
        with tempfile.TemporaryDirectory() as directory:
            outcome = execute(self.spec([sys.executable, "-c", "import time; time.sleep(0.2)"]), directory, approval=True, timeout=0.01)
            self.assertEqual(outcome.status, "failed")
            self.assertTrue(outcome.timed_out)
            self.assertIsNone(outcome.returncode)

    def test_missing_workspace_is_rejected(self):
        missing = str(Path(tempfile.gettempdir()) / "noesis-missing-runner-workspace")
        with self.assertRaises(RunnerConfigurationError):
            prepare(self.spec([sys.executable, "-c", "print('x')"]), missing, approval=True)


if __name__ == "__main__":
    unittest.main()

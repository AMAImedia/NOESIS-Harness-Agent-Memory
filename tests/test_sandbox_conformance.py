from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from noesis_harness.sandbox_backend import inspect_backend, run_conformance
from noesis_harness.sandbox_bwrap import BubblewrapBackend
from noesis_harness.sandbox_macos import MacOSSandboxBackend


class SandboxConformanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_bubblewrap_common_conformance_on_linux_host(self):
        backend = BubblewrapBackend()
        result = inspect_backend(backend, workspace=self.workspace)
        if not backend.available:
            self.assertEqual(result.as_dict()["status"], "not_run")
        else:
            self.assertTrue(result.passed, result.as_dict())
            command = backend.command(("/usr/bin/printf", "ok"), self.workspace)
            self.assertIn("--unshare-net", command)

    def test_macos_backend_is_fail_closed_off_macos(self):
        backend = MacOSSandboxBackend()
        result = inspect_backend(backend, workspace=self.workspace)
        if backend.available:
            self.assertEqual(backend.host_platform, "macos")
        else:
            self.assertFalse(result.available)
            self.assertEqual(result.as_dict()["status"], "not_run")
            with self.assertRaises(Exception):
                backend.command(("/usr/bin/printf", "ok"), self.workspace)

    def test_available_linux_backend_runs_bounded_workspace_probe(self):
        backend = BubblewrapBackend()
        result = run_conformance(backend, workspace=self.workspace)
        if backend.available:
            self.assertTrue(result.passed, result.as_dict())
            names = {name for name, _ in result.checks}
            self.assertTrue({"execution_runner", "workspace_write", "process_exit"}.issubset(names))
        else:
            self.assertEqual(result.as_dict()["status"], "not_run")

    def test_backend_without_run_method_is_not_claimed_passed(self):
        class CommandOnly:
            backend_id = "synthetic-command-only"
            host_platform = "synthetic"
            available = True

            def command(self, argv, workspace):
                return ["/sandbox", "--unshare-net", str(workspace), *argv]

        result = run_conformance(CommandOnly(), workspace=self.workspace)
        self.assertEqual(result.as_dict()["status"], "failed")
        self.assertEqual(result.reason, "backend_run_method_required")

    def test_common_result_declares_each_check(self):
        result = inspect_backend(BubblewrapBackend(executable="missing-bwrap"), workspace=self.workspace)
        record = result.as_dict()
        self.assertEqual(record["backend_id"], "linux-bubblewrap")
        self.assertIn(record["status"], {"passed", "not_run", "failed"})
        self.assertIn("checks", record)


if __name__ == "__main__":
    unittest.main()

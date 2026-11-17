from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from noesis_harness.sandbox_backend import inspect_backend, run_conformance
from noesis_harness.sandbox_bwrap import BubblewrapBackend
from noesis_harness.sandbox_macos import MacOSSandboxBackend
from noesis_harness import sandbox_windows
from noesis_harness.sandbox_windows import hardening_inventory
from scripts.run_sandbox_conformance import build_report


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


class SandboxConformanceReportTests(unittest.TestCase):
    def test_report_carries_windows_hardening_inventory(self):
        report = build_report()
        self.assertEqual(report["schema_version"], "noesis.sandbox-conformance.v2")
        inventory = report["windows_hardening_inventory"]
        self.assertEqual(inventory, hardening_inventory())
        self.assertEqual(inventory["schema_version"], "noesis.windows-hardening-inventory.v1")
        self.assertFalse(inventory["boundary_verified"])
        self.assertEqual(inventory["execution_claim"], "not_run")
        self.assertFalse(inventory["command_builder_present"])
        self.assertIn("appcontainer_or_restricted_token", inventory["boundary_required"])

    def test_hardening_inventory_is_subprocess_free_and_deterministic(self):
        self.assertEqual(hardening_inventory(), hardening_inventory())
        self.assertNotIn("subprocess", vars(sandbox_windows))

    def test_report_rendering_is_deterministic_across_calls(self):
        tempdir_pattern = re.compile(r"[^\"]*noesis-sandbox-conformance-[^\"]*")

        def render():
            return json.dumps(build_report(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"

        first = render()
        second = render()
        normalized_first = tempdir_pattern.sub("<TMPDIR>", first)
        normalized_second = tempdir_pattern.sub("<TMPDIR>", second)
        self.assertEqual(normalized_first, normalized_second)
        self.assertNotIn("noesis-sandbox-conformance-", first)
        self.assertNotIn("<TMPDIR>", first)


if __name__ == "__main__":
    unittest.main()

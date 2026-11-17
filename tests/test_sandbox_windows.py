"""Fail-closed tests for the Windows hardened backend scaffold."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from noesis_harness import sandbox_windows
from noesis_harness.sandbox_backend import inspect_backend, run_conformance
from noesis_harness.sandbox_bwrap import SandboxUnavailable
from noesis_harness.sandbox_windows import WindowsSandboxBackend, hardening_inventory


class WindowsSandboxBackendTests(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(tempfile.mkdtemp(prefix="noesis_sandbox_win_"))

    def test_default_backend_is_unavailable_and_never_passes(self):
        backend = WindowsSandboxBackend()
        self.assertFalse(backend.available)
        result = run_conformance(backend, workspace=self.workspace)
        self.assertFalse(result.available)
        self.assertEqual(result.as_dict()["status"], "not_run")
        self.assertNotEqual(result.as_dict()["status"], "passed")

    def test_inventory_reports_not_run_execution_claim(self):
        inventory = hardening_inventory()
        self.assertFalse(inventory["boundary_verified"])
        self.assertEqual(inventory["execution_claim"], "not_run")

    def test_verifier_without_builder_stays_unavailable(self):
        with patch.object(os, "name", "nt"):
            backend = WindowsSandboxBackend(boundary_verifier=lambda: True)
            self.assertFalse(backend.available)
            self.assertEqual(backend.unavailability_reason(), "windows_command_builder_missing")

    def test_non_windows_host_blocks_even_full_configuration(self):
        if os.name == "nt":
            self.skipTest("requires non-windows host simulation")
        backend = WindowsSandboxBackend(boundary_verifier=lambda: True, command_builder=lambda argv, ws: ["stub", "--"] + list(argv))
        self.assertFalse(backend.available)

    def test_command_raises_when_unavailable(self):
        with self.assertRaises(SandboxUnavailable):
            WindowsSandboxBackend().command(("python3", "-c", "print(1)"), self.workspace)

    def test_run_returns_blocked_without_subprocess_on_this_host(self):
        backend = WindowsSandboxBackend()
        result = backend.run(("python3", "-c", "print(1)"), self.workspace)
        self.assertEqual(result.status, "blocked")
        self.assertIsNone(result.returncode)
        self.assertTrue(result.reason)

    def test_module_never_imports_subprocess(self):
        self.assertNotIn("subprocess", vars(sandbox_windows))

    def test_configured_builder_contract_is_enforced(self):
        calls = []

        def verifier():
            return True

        def builder(argv, workspace):
            calls.append((tuple(argv), workspace))
            return ["wrap", "--root", str(workspace), "--", *argv]

        with patch.object(os, "name", "nt"):
            partial = WindowsSandboxBackend(boundary_verifier=verifier)
            self.assertFalse(partial.available)
            full = WindowsSandboxBackend(boundary_verifier=verifier, command_builder=builder)
            self.assertTrue(full.available)
            command = full.command(("py", "-c", "1"), self.workspace)
            self.assertIn("--", command)
            inspected = inspect_backend(full, workspace=self.workspace)
            self.assertNotEqual(inspected.as_dict()["status"], "not_run")
        self.assertEqual(len(calls), 2)

    def test_repeated_inspection_is_deterministic(self):
        backend = WindowsSandboxBackend()
        first = run_conformance(backend, workspace=self.workspace).as_dict()
        second = run_conformance(backend, workspace=self.workspace).as_dict()
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main(verbosity=2)

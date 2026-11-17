"""Fail-closed tests for the AppContainer backend scaffold."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from noesis_harness import appcontainer_backend
from noesis_harness.appcontainer_backend import (
    AppContainerBackend,
    hardening_inventory_appcontainer,
)
from noesis_harness.sandbox_backend import run_conformance


def _raising_verifier():
    raise RuntimeError("probe exploded")


class AppContainerBackendTests(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(tempfile.mkdtemp(prefix="noesis_appcontainer_"))

    def test_default_backend_is_unavailable_and_never_passes(self):
        backend = AppContainerBackend()
        self.assertFalse(backend.available)
        result = run_conformance(backend, workspace=self.workspace)
        self.assertFalse(result.available)
        self.assertEqual(result.as_dict()["status"], "not_run")
        self.assertNotEqual(result.as_dict()["status"], "passed")

    def test_backend_id_matches_spec_value(self):
        self.assertEqual(AppContainerBackend.backend_id, "model-task-appcontainer")
        self.assertEqual(AppContainerBackend.host_platform, "windows")

    def test_inventory_reports_not_run_claim_and_false_capabilities(self):
        inventory = hardening_inventory_appcontainer()
        self.assertEqual(inventory["execution_claim"], "not_run")
        self.assertFalse(inventory["boundary_verified"])
        self.assertFalse(inventory["command_builder_present"])
        self.assertTrue(inventory["capabilities_required"])
        for name in inventory["capabilities_required"]:
            self.assertIs(inventory["capabilities_verified"][name], False)

    def test_non_windows_host_blocks_even_full_configuration(self):
        with patch.object(os, "name", "posix"):
            backend = AppContainerBackend(
                profile_name="NoesisModelTask",
                allowlisted_hosts=("api.model.example",),
                verify_profile=lambda: True,
            )
            self.assertFalse(backend.available)
            self.assertEqual(backend.unavailability_reason(), "not_windows_host")

    def test_ctypes_unavailable_blocks_with_machine_readable_reason(self):
        with patch.object(os, "name", "nt"), patch.object(appcontainer_backend, "_has_windll", lambda: False):
            backend = AppContainerBackend(profile_name="NoesisModelTask", verify_profile=lambda: True)
            self.assertFalse(backend.available)
            self.assertEqual(backend.unavailability_reason(), "ctypes_unavailable")

    def test_verifier_without_profile_stays_unavailable(self):
        with patch.object(os, "name", "nt"), patch.object(appcontainer_backend, "_has_windll", lambda: True):
            backend = AppContainerBackend(verify_profile=lambda: True)
            self.assertFalse(backend.available)
            self.assertEqual(backend.unavailability_reason(), "appcontainer_profile_missing")

    def test_profile_without_verifier_reports_default_reason(self):
        with patch.object(os, "name", "nt"), patch.object(appcontainer_backend, "_has_windll", lambda: True):
            backend = AppContainerBackend(profile_name="NoesisModelTask")
            self.assertFalse(backend.available)
            self.assertEqual(
                backend.unavailability_reason(),
                appcontainer_backend.DEFAULT_UNAVAILABLE_REASON,
            )

    def test_probe_failure_reports_probe_failed_reason(self):
        with patch.object(os, "name", "nt"), patch.object(appcontainer_backend, "_has_windll", lambda: True):
            failing = AppContainerBackend(profile_name="NoesisModelTask", verify_profile=lambda: False)
            raising = AppContainerBackend(profile_name="NoesisModelTask", verify_profile=_raising_verifier)
            self.assertEqual(failing.unavailability_reason(), "appcontainer_probe_failed")
            self.assertEqual(raising.unavailability_reason(), "appcontainer_probe_failed")
            self.assertFalse(failing.available)
            self.assertFalse(raising.available)

    def test_fully_configured_backend_is_available_but_run_stays_blocked(self):
        with patch.object(os, "name", "nt"), patch.object(appcontainer_backend, "_has_windll", lambda: True):
            backend = AppContainerBackend(
                profile_name="NoesisModelTask",
                allowlisted_hosts=("api.model.example",),
                verify_profile=lambda: True,
            )
            self.assertTrue(backend.available)
            result = backend.run(("python", "-c", "print(1)"), self.workspace)
            self.assertEqual(result.status, "blocked")
            self.assertIsNone(result.returncode)
            self.assertEqual(result.reason, appcontainer_backend.REASON_EXECUTION_NOT_BOUND)

    def test_run_returns_blocked_without_subprocess_on_this_host(self):
        backend = AppContainerBackend()
        result = backend.run(("python", "-c", "print(1)"), self.workspace)
        self.assertEqual(result.status, "blocked")
        self.assertIsNone(result.returncode)
        self.assertTrue(result.reason)
        self.assertNotEqual(result.status, "passed")

    def test_run_validates_inputs_before_availability(self):
        backend = AppContainerBackend()
        self.assertEqual(backend.run((), self.workspace).reason, "argv_required")
        missing = self.workspace / "no_such_dir"
        self.assertEqual(
            backend.run(("python", "-c", "1"), missing).reason,
            "workspace_required",
        )

    def test_invalid_allowlist_fails_closed_at_construction(self):
        with self.assertRaises(ValueError):
            AppContainerBackend(profile_name="NoesisModelTask", allowlisted_hosts=("bad host!",))

    def test_blank_profile_name_counts_as_missing(self):
        with patch.object(os, "name", "nt"):
            backend = AppContainerBackend(profile_name="   ", verify_profile=lambda: True)
            self.assertFalse(backend.available)
            self.assertEqual(backend.unavailability_reason(), "appcontainer_profile_missing")

    def test_module_never_imports_subprocess(self):
        self.assertNotIn("subprocess", vars(appcontainer_backend))

    def test_profile_sid_probe_fails_closed_without_windll(self):
        with patch.object(os, "name", "nt"), patch.object(appcontainer_backend, "_has_windll", lambda: False):
            report = appcontainer_backend.profile_sid_probe()
            self.assertIs(report["available"], False)
            self.assertEqual(report["reason"], appcontainer_backend.REASON_CTYPES_UNAVAILABLE)

    def test_profile_sid_probe_fails_closed_on_non_windows(self):
        with patch.object(os, "name", "posix"):
            report = appcontainer_backend.profile_sid_probe()
            self.assertIs(report["available"], False)
            self.assertEqual(report["reason"], appcontainer_backend.REASON_NOT_WINDOWS_HOST)

    def test_profile_sid_probe_never_raises_and_returns_shape(self):
        report = appcontainer_backend.profile_sid_probe()
        self.assertIsInstance(report, dict)
        self.assertIsInstance(report["available"], bool)
        self.assertIsInstance(report["reason"], str)

    def test_profile_sid_probe_propagates_derivation_failure(self):
        with patch.object(appcontainer_backend, "_probe_app_container_sid", lambda: (appcontainer_backend.REASON_SID_DERIVATION_FAILED, "")):
            report = appcontainer_backend.profile_sid_probe()
            self.assertIs(report["available"], False)
            self.assertEqual(report["reason"], appcontainer_backend.REASON_SID_DERIVATION_FAILED)

    def test_profile_sid_probe_reports_ok_with_used_export_on_success(self):
        with patch.object(appcontainer_backend, "_probe_app_container_sid", lambda: ("", "GetAppContainerSid")):
            report = appcontainer_backend.profile_sid_probe()
            self.assertIs(report["available"], True)
            self.assertEqual(report["reason"], "ok:GetAppContainerSid")

    def test_capability_inventory_reports_all_expected_exports(self):
        inventory = appcontainer_backend.capability_inventory()
        expected = {
            "CreateProcessW": "kernel32",
            "InitializeProcThreadAttributeList": "kernel32",
            "UpdateProcThreadAttribute": "kernel32",
            "GetAppContainerSid": "userenv",
        }
        for name, library in expected.items():
            self.assertIn(name, inventory["functions"])
            entry = inventory["functions"][name]
            self.assertEqual(entry["library"], library)
            self.assertIsInstance(entry["callable"], bool)
        self.assertIs(inventory["execution_bound"], False)
        self.assertEqual(inventory["claim"], "api_presence_does_not_bind_execution")

    def test_capability_inventory_is_deterministic(self):
        first = appcontainer_backend.capability_inventory()
        second = appcontainer_backend.capability_inventory()
        self.assertEqual(first, second)

    def test_capability_inventory_fails_closed_without_windll(self):
        with patch.object(appcontainer_backend, "_has_windll", lambda: False):
            inventory = appcontainer_backend.capability_inventory()
            self.assertIs(inventory["windll_present"], False)
            self.assertIs(inventory["execution_bound"], False)
            for entry in inventory["functions"].values():
                self.assertIs(entry["callable"], False)

    def test_run_probe_never_returns_passed(self):
        backend = AppContainerBackend()
        report = backend.run_probe()
        self.assertIn(report["status"], ("not_run", "blocked"))
        self.assertNotEqual(report["status"], "passed")
        self.assertTrue(report["reason"])
        self.assertIn("capabilities", report)

    def test_run_probe_capabilities_match_inventory(self):
        backend = AppContainerBackend()
        report = backend.run_probe()
        self.assertEqual(report["capabilities"], appcontainer_backend.capability_inventory())

    def test_run_probe_non_windows_reports_not_run(self):
        with patch.object(os, "name", "posix"):
            backend = AppContainerBackend(profile_name="NoesisModelTask", verify_profile=lambda: True)
            report = backend.run_probe()
            self.assertEqual(report["status"], "not_run")
            self.assertEqual(report["reason"], appcontainer_backend.REASON_NOT_WINDOWS_HOST)

    def test_run_probe_configured_backend_is_blocked_execution_not_bound(self):
        with patch.object(os, "name", "nt"), patch.object(appcontainer_backend, "_has_windll", lambda: True):
            backend = AppContainerBackend(profile_name="NoesisModelTask", verify_profile=lambda: True)
            self.assertTrue(backend.available)
            report = backend.run_probe()
            self.assertEqual(report["status"], "blocked")
            self.assertEqual(report["reason"], appcontainer_backend.REASON_EXECUTION_NOT_BOUND)

    def test_repeated_inspection_is_deterministic(self):
        with patch.object(os, "name", "nt"), patch.object(appcontainer_backend, "_has_windll", lambda: True):
            backend = AppContainerBackend(profile_name="NoesisModelTask", verify_profile=lambda: False)
            first = run_conformance(backend, workspace=self.workspace).as_dict()
            second = run_conformance(backend, workspace=self.workspace).as_dict()
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main(verbosity=2)

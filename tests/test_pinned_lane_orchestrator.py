import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.pinned_lane_orchestrator import prepare_matrix, validate_pinned_manifest


def _install_fake_executable(directory: str, name: str) -> None:
    filename = name + (".exe" if os.name == "nt" else "")
    path = Path(directory) / filename
    path.write_bytes(b"")
    path.chmod(0o755)


class PinnedLaneOrchestratorTests(unittest.TestCase):
    def test_three_external_lanes_are_planned_but_not_run_without_pins(self):
        manifest = {"systems": ["noesis", "hermes", "opencode", "deepseek_harness"], "revisions": {"hermes": "", "opencode": "", "deepseek_harness": ""}, "tasks": []}
        with tempfile.TemporaryDirectory() as sanitized_path:
            with mock.patch.dict(os.environ, {"PATH": sanitized_path}):
                report = prepare_matrix(manifest, "/tmp")
        self.assertEqual(report["schema_version"], "noesis.pinned-lane-matrix.v1")
        self.assertEqual(report["external_execution"], "not_run")
        self.assertEqual(report["ranking"], "not_run")
        self.assertEqual(report["manifest_validation"]["status"], "blocked")
        self.assertIn("invalid_manifest_schema", report["manifest_validation"]["errors"])
        self.assertEqual(set(report["adapter_inventory"]), {"hermes", "opencode", "deepseek_harness"})
        for inventory in report["adapter_inventory"].values():
            self.assertFalse(inventory["available"])
            self.assertIsNone(inventory["executable"])
            self.assertEqual(inventory["capability_preflight"]["status"], "not_run")
            self.assertEqual(inventory["execution"], "not_run")
        self.assertEqual(set(report["lanes"]), {"hermes", "opencode", "deepseek_harness"})
        for lane in report["lanes"].values():
            self.assertEqual(lane["execution"], "not_run")
            self.assertEqual(lane["reason"], "missing_exact_revision")

    def test_discovered_executable_is_preflight_ready_for_operator_approval_and_not_executed(self):
        manifest = {"systems": ["noesis", "hermes", "opencode", "deepseek_harness"], "revisions": {"hermes": "", "opencode": "", "deepseek_harness": ""}, "tasks": []}
        with tempfile.TemporaryDirectory() as sanitized_path:
            _install_fake_executable(sanitized_path, "hermes")
            with mock.patch.dict(os.environ, {"PATH": sanitized_path}):
                report = prepare_matrix(manifest, "/tmp")
        hermes_inventory = report["adapter_inventory"]["hermes"]
        self.assertTrue(hermes_inventory["available"])
        self.assertIsNotNone(hermes_inventory["executable"])
        self.assertEqual(hermes_inventory["capability_preflight"]["status"], "ready_for_operator_approval")
        self.assertEqual(hermes_inventory["execution"], "not_run")
        for system in ("opencode", "deepseek_harness"):
            inventory = report["adapter_inventory"][system]
            self.assertFalse(inventory["available"])
            self.assertIsNone(inventory["executable"])
            self.assertEqual(inventory["capability_preflight"]["status"], "not_run")
            self.assertEqual(inventory["execution"], "not_run")
        self.assertEqual(report["external_execution"], "not_run")
        self.assertEqual(report["ranking"], "not_run")
        for lane in report["lanes"].values():
            self.assertEqual(lane["execution"], "not_run")

    def test_invalid_pinned_manifest_is_blocked_after_revision_is_present(self):
        manifest = {
            "schema_version": "noesis.external-ab.v1",
            "revision_policy": "pin_exact_commit_before_run",
            "systems": ["noesis", "hermes", "opencode", "deepseek_harness"],
            "revisions": {"hermes": "main", "opencode": "", "deepseek_harness": ""},
            "workspace": {"disposable": True, "seed_sha256_required": True, "outside_workspace_access": "deny", "model_artifacts": "not_allowed"},
            "budgets": {"network": "deny_by_default", "wall_time_seconds": 300, "agent_steps": 20},
        }
        self.assertIn("revision_not_exact:hermes", validate_pinned_manifest(manifest))
        self.assertIn("missing_seed_digest", validate_pinned_manifest(manifest))
        report = prepare_matrix(manifest, "/tmp")
        self.assertEqual(report["lanes"]["hermes"]["status"], "blocked")
        self.assertEqual(report["lanes"]["hermes"]["reason"], "invalid_pinned_manifest")

    def test_missing_manifest_system_is_reported(self):
        report = prepare_matrix({"systems": ["noesis", "hermes", "opencode"], "revisions": {}, "tasks": []}, "/tmp")
        self.assertEqual(report["missing_manifest_systems"], ["deepseek_harness"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

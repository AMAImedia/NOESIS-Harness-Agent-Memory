import unittest

from scripts.pinned_lane_orchestrator import prepare_matrix, validate_pinned_manifest


class PinnedLaneOrchestratorTests(unittest.TestCase):
    def test_three_external_lanes_are_planned_but_not_run_without_pins(self):
        report = prepare_matrix({"systems": ["noesis", "hermes", "opencode", "deepseek_harness"], "revisions": {"hermes": "", "opencode": "", "deepseek_harness": ""}, "tasks": []}, "/tmp")
        self.assertEqual(report["schema_version"], "noesis.pinned-lane-matrix.v1")
        self.assertEqual(report["external_execution"], "not_run")
        self.assertEqual(report["ranking"], "not_run")
        self.assertEqual(report["manifest_validation"]["status"], "blocked")
        self.assertIn("invalid_manifest_schema", report["manifest_validation"]["errors"])
        self.assertEqual(report["adapter_inventory"]["hermes"]["capability_preflight"]["status"], "not_run")
        self.assertEqual(set(report["lanes"]), {"hermes", "opencode", "deepseek_harness"})
        for lane in report["lanes"].values():
            self.assertEqual(lane["execution"], "not_run")
            self.assertEqual(lane["reason"], "missing_exact_revision")

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

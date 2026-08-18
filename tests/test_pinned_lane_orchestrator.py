import unittest

from scripts.pinned_lane_orchestrator import prepare_matrix


class PinnedLaneOrchestratorTests(unittest.TestCase):
    def test_three_external_lanes_are_planned_but_not_run_without_pins(self):
        report = prepare_matrix({"systems": ["noesis", "hermes", "opencode", "deepseek_harness"], "revisions": {"hermes": "", "opencode": "", "deepseek_harness": ""}, "tasks": []}, "/tmp")
        self.assertEqual(report["schema_version"], "noesis.pinned-lane-matrix.v1")
        self.assertEqual(report["external_execution"], "not_run")
        self.assertEqual(report["ranking"], "not_run")
        self.assertEqual(set(report["lanes"]), {"hermes", "opencode", "deepseek_harness"})
        for lane in report["lanes"].values():
            self.assertEqual(lane["execution"], "not_run")
            self.assertEqual(lane["reason"], "missing_exact_revision")

    def test_missing_manifest_system_is_reported(self):
        report = prepare_matrix({"systems": ["noesis", "hermes", "opencode"], "revisions": {}, "tasks": []}, "/tmp")
        self.assertEqual(report["missing_manifest_systems"], ["deepseek_harness"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

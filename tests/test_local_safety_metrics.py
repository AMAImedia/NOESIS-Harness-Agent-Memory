from __future__ import annotations

import unittest

from scripts.local_safety_metrics import run


class LocalSafetyMetricsTests(unittest.TestCase):
    def test_deterministic_local_metrics_pass_without_ranking(self):
        report = run()
        self.assertEqual(report["schema_version"], "noesis.local-safety-metrics.v1")
        self.assertTrue(report["simulation_only"])
        self.assertIn("no ranking", report["scope"])
        self.assertEqual(report["summary"]["failed"], 0)
        self.assertEqual(report["summary"]["passed"], 5)
        self.assertEqual(report["summary"]["not_run"], 1)
        self.assertTrue(report["summary"]["provider_invocation_probe"])

    def test_security_and_boundary_metrics_are_observed(self):
        metrics = run()["metrics"]
        self.assertEqual(metrics["credential_exposure"]["details"]["cases"], 21)
        self.assertEqual(metrics["credential_exposure"]["details"]["passed"], 21)
        for name in ("patch_correctness", "recovery", "unauthorized_egress", "approval_bypass"):
            self.assertEqual(metrics[name]["status"], "observed")
            self.assertTrue(metrics[name]["passed"], name)
        self.assertEqual(metrics["human_review_seconds"]["status"], "not_run")


if __name__ == "__main__":
    unittest.main()

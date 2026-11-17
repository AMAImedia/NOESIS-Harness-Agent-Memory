import unittest

from scripts.build_comparative_report import build_report
from tests.test_external_evidence_readiness import KEY, evidence_for, manifest


class ComparativeReportTests(unittest.TestCase):
    def test_missing_pins_is_not_run_and_has_no_score(self):
        report = build_report({"revisions": {}}, [], KEY)
        self.assertEqual(report["score_status"], "not_run")
        self.assertFalse(report["score_claim"])
        self.assertFalse(report["readiness"]["comparative_ready"])
        self.assertEqual(report["lanes"]["hermes"]["status"], "not_run")

    def test_partial_signed_evidence_cannot_create_comparative_score(self):
        report = build_report(manifest(), [evidence_for("hermes", "h1"), evidence_for("opencode", "o1")], KEY)
        self.assertFalse(report["score_claim"])
        self.assertEqual(report["reason"], "external_execution_not_ready")
        self.assertEqual(report["lanes"]["deepseek_harness"]["status"], "blocked")

    def test_all_required_lanes_are_ready_but_case_score_is_still_not_fabricated(self):
        evidence = [evidence_for("hermes", "h1"), evidence_for("opencode", "o1"), evidence_for("deepseek_harness", "d1")]
        report = build_report(manifest(), evidence, KEY)
        self.assertTrue(report["readiness"]["comparative_ready"])
        self.assertEqual(report["score_status"], "not_run")
        self.assertFalse(report["score_claim"])
        self.assertEqual(report["reason"], "case_level_scoring_not_ingested")
        self.assertTrue(all(item["signed_evidence_verified"] for item in report["lanes"].values()))

    def test_tampered_receipt_blocks_lane_and_report(self):
        record = dict(evidence_for("hermes", "h1"))
        record["metrics"] = {"task_success": {"status": "observed", "value": 0.0}}
        report = build_report(manifest(), [record], KEY)
        self.assertEqual(report["lanes"]["hermes"]["status"], "blocked")
        self.assertFalse(report["score_claim"])

    def test_duplicate_system_record_is_blocked(self):
        report = build_report(manifest(), [evidence_for("hermes", "h1"), evidence_for("hermes", "h1")], KEY)
        self.assertEqual(report["lanes"]["hermes"]["status"], "blocked")
        self.assertFalse(report["score_claim"])


if __name__ == "__main__":
    unittest.main()

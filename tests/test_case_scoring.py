import unittest

from scripts.build_comparative_report import create_case_receipt, build_report
from tests.test_external_evidence_readiness import KEY, evidence_for, manifest


DIMENSIONS = {
    "task_correctness": {"status": "observed", "value": 1.0},
    "patch_correctness": {"status": "observed", "value": 1.0},
    "recovery": {"status": "observed", "value": 0.5},
    "isolation_egress": {"status": "observed", "value": 1.0},
    "cross_agent_leakage": {"status": "observed", "value": 1.0},
    "long_context_use": {"status": "observed", "value": 0.75},
    "review_burden": {"status": "observed", "value": 1.0},
}


def cases(case_ids=("case-a", "case-b"), safety_failures=()):
    return [
        create_case_receipt(system=lane, revision=revision, protocol_fingerprint="a" * 64, case_id=case_id, evaluator_revision="eval-1", dimensions=DIMENSIONS, safety_failures=safety_failures, key=KEY)
        for lane, revision in (("hermes", "h1"), ("opencode", "o1"), ("deepseek_harness", "d1"))
        for case_id in case_ids
    ]


class CaseScoringTests(unittest.TestCase):
    def test_complete_signed_corpus_aggregates_deterministically(self):
        lane_evidence = [evidence_for("hermes", "h1"), evidence_for("opencode", "o1"), evidence_for("deepseek_harness", "d1")]
        manifest_value = manifest(protocol_fingerprint=lane_evidence[0]["protocol_fingerprint"], case_ids=["case-a", "case-b"])
        report = build_report(manifest_value, lane_evidence, KEY, [create_case_receipt(system=lane, revision=revision, protocol_fingerprint=manifest_value["protocol_fingerprint"], case_id=case_id, evaluator_revision="eval-1", dimensions=DIMENSIONS, key=KEY) for lane, revision in (("hermes", "h1"), ("opencode", "o1"), ("deepseek_harness", "d1")) for case_id in manifest_value["case_ids"]])
        self.assertTrue(report["score_available"])
        self.assertEqual(report["score_status"], "available")
        self.assertEqual(report["case_aggregates"]["hermes"]["case_count"], 2)
        self.assertEqual(report["case_aggregates"]["hermes"]["dimension_means"]["recovery"], 0.5)
        self.assertFalse(report["score_claim"])
        self.assertEqual(report["cross_lane_dimension_means"]["recovery"], 0.5)

    def test_incomplete_dimension_record_is_blocked(self):
        lane_evidence = [evidence_for("hermes", "h1"), evidence_for("opencode", "o1"), evidence_for("deepseek_harness", "d1")]
        manifest_value = manifest(protocol_fingerprint=lane_evidence[0]["protocol_fingerprint"], case_ids=["case-a"])
        incomplete = dict(DIMENSIONS)
        incomplete.pop("recovery")
        cases = [create_case_receipt(system=lane, revision=revision, protocol_fingerprint=manifest_value["protocol_fingerprint"], case_id="case-a", evaluator_revision="eval-1", dimensions=incomplete, key=KEY) for lane, revision in (("hermes", "h1"), ("opencode", "o1"), ("deepseek_harness", "d1"))]
        report = build_report(manifest_value, lane_evidence, KEY, cases)
        self.assertFalse(report["score_available"])
        self.assertEqual(report["score_status"], "blocked")
        self.assertTrue(any(item.startswith("invalid_case_receipt") for item in report["case_errors"]))

    def test_unobserved_numeric_dimension_is_blocked(self):
        lane_evidence = [evidence_for("hermes", "h1"), evidence_for("opencode", "o1"), evidence_for("deepseek_harness", "d1")]
        manifest_value = manifest(protocol_fingerprint=lane_evidence[0]["protocol_fingerprint"], case_ids=["case-a"])
        unobserved = {name: dict(value) for name, value in DIMENSIONS.items()}
        unobserved["recovery"]["status"] = "not_run"
        cases = [create_case_receipt(system=lane, revision=revision, protocol_fingerprint=manifest_value["protocol_fingerprint"], case_id="case-a", evaluator_revision="eval-1", dimensions=unobserved, key=KEY) for lane, revision in (("hermes", "h1"), ("opencode", "o1"), ("deepseek_harness", "d1"))]
        report = build_report(manifest_value, lane_evidence, KEY, cases)
        self.assertFalse(report["score_available"])
        self.assertEqual(report["score_status"], "blocked")
        self.assertTrue(any(item.startswith("invalid_case_receipt") for item in report["case_errors"]))

    def test_missing_case_is_blocked_and_not_imputed(self):
        lane_evidence = [evidence_for("hermes", "h1"), evidence_for("opencode", "o1"), evidence_for("deepseek_harness", "d1")]
        manifest_value = manifest(protocol_fingerprint=lane_evidence[0]["protocol_fingerprint"], case_ids=["case-a", "case-b"])
        report = build_report(manifest_value, lane_evidence, KEY, [create_case_receipt(system=lane, revision=revision, protocol_fingerprint=manifest_value["protocol_fingerprint"], case_id="case-a", evaluator_revision="eval-1", dimensions=DIMENSIONS, key=KEY) for lane, revision in (("hermes", "h1"), ("opencode", "o1"), ("deepseek_harness", "d1"))])
        self.assertFalse(report["score_available"])
        self.assertEqual(report["score_status"], "blocked")
        self.assertIn("missing_case:hermes:case-b", report["case_errors"])

    def test_mandatory_safety_failure_blocks_score(self):
        lane_evidence = [evidence_for("hermes", "h1"), evidence_for("opencode", "o1"), evidence_for("deepseek_harness", "d1")]
        manifest_value = manifest(protocol_fingerprint=lane_evidence[0]["protocol_fingerprint"], case_ids=["case-a"])
        safety_cases = [create_case_receipt(system=lane, revision=revision, protocol_fingerprint=manifest_value["protocol_fingerprint"], case_id="case-a", evaluator_revision="eval-1", dimensions=DIMENSIONS, safety_failures=("credential_leakage",), key=KEY) for lane, revision in (("hermes", "h1"), ("opencode", "o1"), ("deepseek_harness", "d1"))]
        report = build_report(manifest_value, lane_evidence, KEY, safety_cases)
        self.assertFalse(report["score_available"])
        self.assertEqual(report["score_status"], "blocked")
        self.assertIn("credential_leakage", report["case_aggregates"]["hermes"]["safety_failures"])

    def test_case_identity_mismatch_is_blocked(self):
        lane_evidence = [evidence_for("hermes", "h1"), evidence_for("opencode", "o1"), evidence_for("deepseek_harness", "d1")]
        manifest_value = manifest(protocol_fingerprint=lane_evidence[0]["protocol_fingerprint"], case_ids=["case-a"])
        mismatched = [create_case_receipt(system=lane, revision=("other" if lane == "hermes" else revision), protocol_fingerprint=manifest_value["protocol_fingerprint"], case_id="case-a", evaluator_revision="eval-1", dimensions=DIMENSIONS, key=KEY) for lane, revision in (("hermes", "h1"), ("opencode", "o1"), ("deepseek_harness", "d1"))]
        report = build_report(manifest_value, lane_evidence, KEY, mismatched)
        self.assertFalse(report["score_available"])
        self.assertIn("case_identity_mismatch:hermes:case-a", report["case_errors"])

    def test_case_tamper_and_duplicate_are_blocked(self):
        lane_evidence = [evidence_for("hermes", "h1"), evidence_for("opencode", "o1"), evidence_for("deepseek_harness", "d1")]
        manifest_value = manifest(protocol_fingerprint=lane_evidence[0]["protocol_fingerprint"], case_ids=["case-a"])
        lane_cases = [create_case_receipt(system=lane, revision=revision, protocol_fingerprint=manifest_value["protocol_fingerprint"], case_id="case-a", evaluator_revision="eval-1", dimensions=DIMENSIONS, key=KEY) for lane, revision in (("hermes", "h1"), ("opencode", "o1"), ("deepseek_harness", "d1"))]
        lane_cases[0]["dimensions"]["recovery"]["value"] = 0.0
        report = build_report(manifest_value, lane_evidence, KEY, lane_cases + [lane_cases[1]])
        self.assertFalse(report["score_available"])
        self.assertTrue(any(item.startswith("invalid_case_receipt") for item in report["case_errors"]))


if __name__ == "__main__":
    unittest.main()

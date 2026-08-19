import unittest

from scripts.build_operator_case_bundle import build_bundle
from scripts.validate_operator_import import validate_import
from tests.test_case_scoring import DIMENSIONS, KEY
from tests.test_external_evidence_readiness import evidence_for, manifest
from scripts.build_comparative_report import create_case_receipt


class OperatorImportTests(unittest.TestCase):
    def bundle_manifest(self):
        lane_evidence = [evidence_for("hermes", "h1"), evidence_for("opencode", "o1"), evidence_for("deepseek_harness", "d1")]
        value = manifest(protocol_fingerprint=lane_evidence[0]["protocol_fingerprint"], case_ids=["case-a"])
        value["revisions"] = {"hermes": "h1", "opencode": "o1", "deepseek_harness": "d1"}
        return value, lane_evidence

    def test_import_is_not_run_without_external_evidence(self):
        value, evidence = self.bundle_manifest()
        bundle = build_bundle(value)
        result = validate_import(bundle, value, [], [], KEY)
        self.assertEqual(result["status"], "accepted_not_run")
        self.assertFalse(result["score_claim"])
        self.assertFalse(result["external_execution_claim"])

    def test_bundle_tamper_is_blocked(self):
        value, _ = self.bundle_manifest()
        bundle = build_bundle(value)
        bundle["case_ids"] = ["drifted"]
        result = validate_import(bundle, value, [], [], KEY)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("bundle_digest_mismatch", result["errors"])

    def test_manifest_drift_is_blocked(self):
        value, _ = self.bundle_manifest()
        bundle = build_bundle(value)
        changed = dict(value)
        changed["case_ids"] = ["other"]
        result = validate_import(bundle, changed, [], [], KEY)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("manifest_drift", result["errors"])

    def test_lane_revision_drift_is_blocked(self):
        value, evidence = self.bundle_manifest()
        bundle = build_bundle(value)
        changed = dict(evidence[0])
        changed["revision"] = "wrong"
        result = validate_import(bundle, value, [changed], [], KEY)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("lane_revision_drift:hermes", result["errors"])

    def test_complete_signed_import_still_does_not_claim_superiority(self):
        value, evidence = self.bundle_manifest()
        bundle = build_bundle(value)
        cases = [create_case_receipt(system=lane, revision=revision, protocol_fingerprint=value["protocol_fingerprint"], case_id="case-a", evaluator_revision="eval-1", dimensions=DIMENSIONS, key=KEY) for lane, revision in (("hermes", "h1"), ("opencode", "o1"), ("deepseek_harness", "d1"))]
        result = validate_import(bundle, value, evidence, cases, KEY)
        self.assertFalse(result["score_claim"])
        self.assertFalse(result["external_execution_claim"])


if __name__ == "__main__":
    unittest.main()

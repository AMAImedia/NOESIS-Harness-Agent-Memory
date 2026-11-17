import unittest

from scripts.aggregate_external_evidence import aggregate_external_evidence, verify_aggregate
from tests.test_external_evidence_readiness import evidence_for, manifest

KEY = "readiness-test-key-2026"


class AggregateExternalEvidenceTests(unittest.TestCase):
    def lanes(self):
        return [evidence_for("hermes", "h1"), evidence_for("opencode", "o1"), evidence_for("deepseek_harness", "d1")]

    def test_signed_aggregate_is_deterministic_and_verifiable(self):
        evidence = self.lanes()
        shared_manifest = manifest(protocol_fingerprint=evidence[0]["protocol_fingerprint"])
        first = aggregate_external_evidence(shared_manifest, evidence, KEY)
        second = aggregate_external_evidence(shared_manifest, list(reversed(evidence)), KEY)
        self.assertEqual(first, second)
        self.assertEqual(first["overall_status"], "passed")
        self.assertTrue(first["comparative_ready"])
        self.assertEqual(verify_aggregate(first, KEY)["status"], "passed")
        self.assertFalse(first["native_or_external_execution_claim"])

    def test_missing_lane_remains_not_run_and_comparison_not_ready(self):
        result = aggregate_external_evidence(manifest(), self.lanes()[:2], KEY)
        self.assertEqual(result["overall_status"], "blocked")
        self.assertFalse(result["comparative_ready"])
        self.assertEqual(result["lanes"]["deepseek_harness"]["status"], "blocked")

    def test_tampered_aggregate_is_rejected(self):
        evidence = self.lanes()
        result = aggregate_external_evidence(manifest(protocol_fingerprint=evidence[0]["protocol_fingerprint"]), evidence, KEY)
        result["comparative_ready"] = False
        self.assertEqual(verify_aggregate(result, KEY)["reason"], "aggregate_digest_mismatch")

    def test_claim_boundary_tamper_is_rejected_after_resigning(self):
        evidence = self.lanes()
        result = aggregate_external_evidence(manifest(protocol_fingerprint=evidence[0]["protocol_fingerprint"]), evidence, KEY)
        result["native_or_external_execution_claim"] = True
        unsigned = {key: value for key, value in result.items() if key not in {"aggregate_digest", "signature"}}
        import hashlib
        import hmac
        import json
        canonical = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        result["aggregate_digest"] = hashlib.sha256(canonical).hexdigest()
        result["signature"] = hmac.new(KEY.encode("utf-8"), canonical, hashlib.sha256).hexdigest()
        self.assertEqual(verify_aggregate(result, KEY)["reason"], "aggregate_claim_boundary_invalid")


if __name__ == "__main__":
    unittest.main()

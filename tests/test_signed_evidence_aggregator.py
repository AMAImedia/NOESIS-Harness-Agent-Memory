import unittest

from noesis_harness.signed_evidence_aggregator import SignedEvidenceAggregator, sign_evidence


class SignedEvidenceAggregatorTests(unittest.TestCase):
    key = b"aggregate-signing-key-1234"

    def record(self, evidence_id, lane, *, status="passed", session_id="session-1", task_id="task-1", request_digest="d" * 64):
        receipt = {"schema_version": "noesis.receipt.v1", "evidence_id": evidence_id, "lane": lane, "session_id": session_id, "task_id": task_id, "request_digest": request_digest, "status": status}
        return {**receipt, "signature": sign_evidence(receipt, self.key), "receipt": receipt}

    def test_all_required_lanes_pass_without_comparative_escalation(self):
        result = SignedEvidenceAggregator(self.key).aggregate([self.record("e1", "delegated"), self.record("e2", "child_runtime")])
        self.assertEqual(result.status, "passed")
        self.assertTrue(result.execution_claim)
        self.assertFalse(result.comparative_claim)
        self.assertEqual(result.lanes, ("child_runtime", "delegated"))

    def test_missing_lane_is_not_run(self):
        result = SignedEvidenceAggregator(self.key).aggregate([self.record("e1", "delegated")])
        self.assertEqual(result.status, "not_run")
        self.assertFalse(result.execution_claim)

    def test_duplicate_and_tamper_are_blocked(self):
        record = self.record("e1", "delegated")
        duplicate = SignedEvidenceAggregator(self.key).aggregate([record, record])
        self.assertEqual(duplicate.reason, "duplicate_evidence_id")
        tampered = dict(record)
        tampered["receipt"] = dict(record["receipt"], task_id="other-task")
        invalid = SignedEvidenceAggregator(self.key).aggregate([tampered, self.record("e2", "child_runtime")])
        self.assertEqual(invalid.reason, "receipt_signature_invalid")

    def test_cross_identity_and_non_passed_records_are_blocked(self):
        mismatch = self.record("e1", "delegated", task_id="task-2")
        mismatch["receipt"] = dict(mismatch["receipt"], task_id="task-1")
        mismatch["signature"] = sign_evidence(mismatch["receipt"], self.key)
        self.assertEqual(SignedEvidenceAggregator(self.key).aggregate([mismatch, self.record("e2", "child_runtime")]).reason, "receipt_identity_mismatch")
        failed = SignedEvidenceAggregator(self.key).aggregate([self.record("e1", "delegated", status="failed"), self.record("e2", "child_runtime")])
        self.assertEqual(failed.reason, "non_passed_evidence_cannot_aggregate")


if __name__ == "__main__":
    unittest.main()

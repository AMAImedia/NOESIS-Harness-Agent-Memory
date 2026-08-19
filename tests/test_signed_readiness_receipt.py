import copy
import unittest

from scripts.release_gate_artifact import build_gate_artifact
from scripts.release_readiness_snapshot import build_snapshot
from scripts.signed_readiness_receipt import sign_readiness_receipt, verify_readiness_receipt

KEY = "readiness-test-key-2026"


class SignedReadinessReceiptTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = build_snapshot({"status": "passed"}, 630, "3.14.7")
        self.gate = build_gate_artifact({"status": "passed", "stages": {"post_transfer_audit": {"status": "passed"}, "release_readiness_snapshot": {"status": "passed"}}})
        self.receipt = sign_readiness_receipt(self.snapshot, self.gate, 630, "3.14.7", KEY)

    def test_valid_binding(self):
        self.assertEqual(verify_readiness_receipt(self.receipt, self.snapshot, self.gate, 630, KEY)["status"], "passed")

    def test_snapshot_gate_and_test_drift(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["snapshot_digest"] = "0" * 64
        self.assertEqual(verify_readiness_receipt(self.receipt, snapshot, self.gate, 630, KEY)["reason"], "readiness_receipt_snapshot_drift")
        gate = copy.deepcopy(self.gate)
        gate["artifact_digest"] = "0" * 64
        self.assertEqual(verify_readiness_receipt(self.receipt, self.snapshot, gate, 630, KEY)["reason"], "readiness_receipt_gate_artifact_drift")
        self.assertEqual(verify_readiness_receipt(self.receipt, self.snapshot, self.gate, 631, KEY)["reason"], "readiness_receipt_test_count_drift")

    def test_signature_and_claim_tampering(self):
        self.assertEqual(verify_readiness_receipt(self.receipt, self.snapshot, self.gate, 630, "different-valid-key")["reason"], "readiness_receipt_signature_invalid")
        tampered = copy.deepcopy(self.receipt)
        tampered["external_execution_claim"] = True
        self.assertEqual(verify_readiness_receipt(tampered, self.snapshot, self.gate, 630, KEY)["reason"], "readiness_receipt_digest_mismatch")


if __name__ == "__main__":
    unittest.main()

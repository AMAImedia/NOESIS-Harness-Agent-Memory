import tempfile
import unittest
from pathlib import Path

from noesis_harness.execution_assurance import AssuranceError, ExecutionReceiptStore, ExecutionRecoveryStore, create_receipt, verify_receipt


class ExecutionAssuranceTests(unittest.TestCase):
    def test_receipt_is_deterministic_and_verifiable(self):
        kwargs = {"request": {"tool": "read"}, "policy": {"capability": "file.read"}, "workspace_before": "sha256:before", "workspace_after": "sha256:after", "outcome": "committed", "rollback_available": True, "side_effects": ("workspace_patch",)}
        first = create_receipt(**kwargs)
        second = create_receipt(**kwargs)
        self.assertEqual(first, second)
        self.assertTrue(verify_receipt(first))

    def test_tampering_is_detected(self):
        receipt = create_receipt(request={"x": 1}, policy={"allow": True}, workspace_before="sha256:b", workspace_after=None, outcome="failed", rollback_available=True)
        object.__setattr__(receipt, "outcome", "committed")
        self.assertFalse(verify_receipt(receipt))

    def test_signed_receipt_store_is_idempotent_and_restart_safe(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "receipts.db")
            key = b"execution-receipt-signing-key"
            store = ExecutionReceiptStore(path, signing_key=key)
            receipt = create_receipt(request={"tool": "read"}, policy={"capability": "file.read"}, workspace_before="sha256:b", workspace_after="sha256:a", outcome="committed", rollback_available=True, signing_key=key)
            self.assertTrue(verify_receipt(receipt, key))
            self.assertEqual(store.put(receipt), receipt)
            reopened = ExecutionReceiptStore(path, signing_key=key)
            self.assertEqual(reopened.get(receipt.receipt_id), receipt)
            with self.assertRaisesRegex(AssuranceError, "invalid_signed_receipt"):
                reopened.put(create_receipt(request={"x": 1}, policy={"allow": True}, workspace_before="sha256:b", workspace_after=None, outcome="failed", rollback_available=True))

    def test_interrupted_recovery_is_explicit_and_never_claims_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "recovery.db")
            store = ExecutionRecoveryStore(path)
            store.begin("run-1", "sha256:before")
            reopened = ExecutionRecoveryStore(path)
            state = reopened.recover("run-1")
            self.assertEqual(state["status"], "interrupted_recovery_required")
            self.assertFalse(state["rollback_performed"])
            self.assertEqual(reopened.mark_recovered("run-1")["status"], "recovered")

    def test_invalid_outcome_fails_closed(self):
        with self.assertRaises(AssuranceError):
            create_receipt(request={}, policy={}, workspace_before="sha256:b", workspace_after=None, outcome="unknown", rollback_available=False)


if __name__ == "__main__":
    unittest.main()

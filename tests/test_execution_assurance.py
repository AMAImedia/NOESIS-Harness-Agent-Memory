import tempfile
import unittest
from pathlib import Path

from noesis_harness.execution_assurance import AssuranceError, ExecutionReceiptStore, ExecutionRecoveryStore, build_artifact_diff, create_receipt, verify_receipt


class ExecutionAssuranceTests(unittest.TestCase):
    def test_receipt_is_deterministic_and_verifiable(self):
        kwargs = {"request": {"tool": "read"}, "policy": {"capability": "file.read"}, "workspace_before": "sha256:before", "workspace_after": "sha256:after", "outcome": "committed", "rollback_available": True, "side_effects": ("workspace_patch",)}
        first = create_receipt(**kwargs)
        second = create_receipt(**kwargs)
        self.assertEqual(first, second)
        self.assertTrue(verify_receipt(first))

    def test_artifact_diff_is_deterministic_and_receipt_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            before = Path(directory) / "before"
            after = Path(directory) / "after"
            before.mkdir()
            after.mkdir()
            (before / "same.txt").write_text("same\n", encoding="utf-8")
            (after / "same.txt").write_text("changed\n", encoding="utf-8")
            (after / "added.txt").write_text("new\n", encoding="utf-8")
            diff = build_artifact_diff(str(before), str(after))
            self.assertEqual(diff["added"], ("added.txt",))
            self.assertEqual(diff["removed"], ())
            self.assertEqual(diff["changed"], ("same.txt",))
            self.assertEqual(diff["digest"], build_artifact_diff(str(before), str(after))["digest"])
            receipt = create_receipt(request={"tool": "child"}, policy={"capability": "workspace_write"}, workspace_before="sha256:before", workspace_after="sha256:after", outcome="committed", rollback_available=True, artifact_diff=diff, signing_key=b"artifact-diff-signing-key")
            self.assertTrue(receipt.artifact_diff_digest)
            self.assertTrue(verify_receipt(receipt, b"artifact-diff-signing-key"))
            object.__setattr__(receipt, "artifact_diff_digest", "sha256:tampered")
            self.assertFalse(verify_receipt(receipt, b"artifact-diff-signing-key"))

    def test_artifact_diff_rejects_missing_workspace(self):
        with self.assertRaisesRegex(AssuranceError, "artifact_workspace_required"):
            build_artifact_diff("/path/that/does/not/exist", None)

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

    def test_terminal_completion_is_idempotent_but_conflicts_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ExecutionRecoveryStore(str(Path(directory) / "recovery.db"))
            store.begin("run-terminal", "sha256:before")
            first = store.complete("run-terminal", workspace_after="sha256:after", receipt_id="receipt-1", status="completed")
            duplicate = store.complete("run-terminal", workspace_after="sha256:after", receipt_id="receipt-1", status="completed")
            self.assertEqual(duplicate["status"], "completed")
            self.assertEqual(duplicate["receipt_id"], first["receipt_id"])
            with self.assertRaisesRegex(AssuranceError, "terminal_conflict"):
                store.complete("run-terminal", workspace_after="sha256:other", receipt_id="receipt-2", status="failed")

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

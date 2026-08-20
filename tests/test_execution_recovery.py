import tempfile
import unittest
from pathlib import Path

from noesis_harness.execution_assurance import ExecutionReceiptStore, ExecutionRecoveryStore, create_receipt
from noesis_harness.execution_recovery import ExecutionRecoveryAction, ExecutionRecoveryError, ExecutionRecoveryExecutor
from noesis_harness.workspaces import PatchProposal, PatchReviewStore


class ExecutionRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.key = b"execution-recovery-signing-key"
        self.receipts = ExecutionReceiptStore(str(root / "receipts.db"), signing_key=self.key)
        self.recovery = ExecutionRecoveryStore(str(root / "recovery.db"))
        self.patches = PatchReviewStore(str(root / "patches.db"))
        self.receipt = create_receipt(request={"tool": "write"}, policy={"capability": "workspace.write"}, workspace_before="sha256:before", workspace_after="sha256:after", outcome="committed", rollback_available=True, signing_key=self.key)
        self.receipts.put(self.receipt)
        self.recovery.begin("run-1", "sha256:before")
        self.recovery.complete("run-1", workspace_after="sha256:after", receipt_id=self.receipt.receipt_id, status="completed")
        proposal = PatchProposal("patch-1", "ws-1", "snap-base", "snap-head", ({"path": "out.txt", "kind": "modified"},), "approved")
        self.patches.put(proposal)
        self.action = ExecutionRecoveryAction("action-1", "rollback", "run-1", self.receipt.receipt_id, "patch-1", "ws-1", "snap-base", "operator-1", "session-1")
        self.context = {"authenticated": True, "operator_id": "operator-1", "session_id": "session-1", "scopes": ("runtime:recovery",)}

    def tearDown(self):
        self.tmp.cleanup()

    def test_authenticated_rollback_requires_handler_and_confirms_actual_transition(self):
        with self.assertRaisesRegex(ExecutionRecoveryError, "rollback_handler_required"):
            ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=str(Path(self.tmp.name) / "events.jsonl")).handle(self.action, self.context)
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=str(Path(self.tmp.name) / "events.jsonl"), rollback_handler=lambda _: True)
        result = executor.handle(self.action, self.context)
        self.assertEqual(result["status"], "rolled_back")
        self.assertTrue(result["rollback_performed"])
        self.assertEqual(self.recovery.get("run-1")["status"], "rolled_back")
        replay = executor.handle(self.action, self.context)
        self.assertEqual(replay["status"], "replayed")

    def test_interrupted_run_requires_explicit_authenticated_recovery(self):
        self.recovery.begin("run-interrupted", "sha256:before", "sha256:request")
        action = ExecutionRecoveryAction("action-recover", "recover", "run-interrupted", "", "proposal-not-required", "ws-1", "snap-base", "operator-1", "session-1")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=str(Path(self.tmp.name) / "recovery-events.jsonl"), rollback_handler=lambda _: True)
        result = executor.handle(action, self.context)
        self.assertEqual(result["status"], "recovered")
        self.assertFalse(result["rollback_performed"])
        self.assertEqual(self.recovery.get("run-interrupted")["status"], "recovered")
        with self.assertRaisesRegex(ExecutionRecoveryError, "interrupted_run_required"):
            executor.handle(ExecutionRecoveryAction("action-recover-again", "recover", "run-interrupted", "", "proposal-not-required", "ws-1", "snap-base", "operator-1", "session-1"), self.context)

    def test_rollback_requires_matching_persisted_chain_snapshot(self):
        prepared = create_receipt(request={"tool": "write"}, policy={"capability": "workspace.write"}, workspace_before="sha256:before", workspace_after=None, outcome="prepared", rollback_available=True, signing_key=self.key)
        self.receipts.put(prepared)
        snapshot = self.receipts.save_chain_snapshot((prepared.receipt_id, self.receipt.receipt_id))
        action = ExecutionRecoveryAction("action-snapshot", "rollback", "run-1", self.receipt.receipt_id, "patch-1", "ws-1", "snap-base", "operator-1", "session-1", chain_snapshot_id=snapshot["snapshot_id"])
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=str(Path(self.tmp.name) / "snapshot-events.jsonl"), rollback_handler=lambda _: True)
        result = executor.handle(action, self.context)
        self.assertEqual(result["status"], "rolled_back")
        self.assertEqual(result["chain_snapshot_id"], snapshot["snapshot_id"])
        self.assertEqual(result["chain_snapshot_digest"], snapshot["snapshot_digest"])

        other_prepared = create_receipt(request={"tool": "other"}, policy={"capability": "workspace.write"}, workspace_before="sha256:before", workspace_after=None, outcome="prepared", rollback_available=True, signing_key=self.key)
        other_committed = create_receipt(request={"tool": "other"}, policy={"capability": "workspace.write"}, workspace_before="sha256:before", workspace_after="sha256:other", outcome="committed", rollback_available=True, signing_key=self.key)
        self.receipts.put(other_prepared)
        self.receipts.put(other_committed)
        stale_snapshot = self.receipts.save_chain_snapshot((other_prepared.receipt_id, other_committed.receipt_id))
        stale_action = ExecutionRecoveryAction("action-stale-snapshot", "rollback", "run-1", self.receipt.receipt_id, "patch-1", "ws-1", "snap-base", "operator-1", "session-1", chain_snapshot_id=stale_snapshot["snapshot_id"])
        with self.assertRaisesRegex(ExecutionRecoveryError, "chain_snapshot_mismatch"):
            executor.handle(stale_action, self.context)

    def test_rollback_rejects_artifact_diff_mismatch(self):
        receipt = create_receipt(request={"tool": "write", "run": "diff"}, policy={"capability": "workspace.write"}, workspace_before="sha256:before", workspace_after="sha256:after", outcome="committed", rollback_available=True, signing_key=self.key, artifact_diff={"digest": "sha256:expected-diff"})
        self.receipts.put(receipt)
        self.recovery.begin("run-diff", "sha256:before")
        self.recovery.complete("run-diff", workspace_after="sha256:after", receipt_id=receipt.receipt_id, status="completed")
        action = ExecutionRecoveryAction("action-diff", "rollback", "run-diff", receipt.receipt_id, "patch-1", "ws-1", "snap-base", "operator-1", "session-1", artifact_diff_digest="sha256:wrong-diff")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=str(Path(self.tmp.name) / "diff-events.jsonl"), rollback_handler=lambda _: True)
        with self.assertRaisesRegex(ExecutionRecoveryError, "artifact_diff_mismatch"):
            executor.handle(action, self.context)

    def test_duplicate_action_id_with_changed_payload_is_rejected(self):
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=str(Path(self.tmp.name) / "replay-events.jsonl"), rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        conflicting = ExecutionRecoveryAction("action-1", "rollback", "run-1", self.receipt.receipt_id, "patch-1", "ws-1", "snap-base", "operator-1", "session-1", artifact_diff_digest="sha256:changed")
        with self.assertRaisesRegex(ExecutionRecoveryError, "replay_conflict"):
            executor.handle(conflicting, self.context)

    def test_rollback_rejects_unauthorized_stale_or_unapproved_state(self):
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=str(Path(self.tmp.name) / "events.jsonl"), rollback_handler=lambda _: True)
        with self.assertRaisesRegex(PermissionError, "scope_denied"):
            executor.handle(self.action, {"authenticated": True, "operator_id": "operator-1", "session_id": "session-1", "scopes": ()})
        stale = ExecutionRecoveryAction("action-stale", "rollback", "run-1", self.receipt.receipt_id, "patch-1", "ws-1", "snap-new", "operator-1", "session-1")
        with self.assertRaisesRegex(ExecutionRecoveryError, "base_stale"):
            executor.handle(stale, self.context)
        self.patches.put(PatchProposal("patch-2", "ws-1", "snap-base", "snap-head", (), "needs_review"))
        unapproved = ExecutionRecoveryAction("action-unapproved", "rollback", "run-1", self.receipt.receipt_id, "patch-2", "ws-1", "snap-base", "operator-1", "session-1")
        with self.assertRaisesRegex(ExecutionRecoveryError, "approved_patch_required"):
            executor.handle(unapproved, self.context)


if __name__ == "__main__":
    unittest.main()

import tempfile
import json
import unittest
from pathlib import Path

from noesis_harness.execution_assurance import ExecutionReceiptStore, ExecutionRecoveryStore, create_receipt
from noesis_harness.execution_recovery import ExecutionRecoveryAction, ExecutionRecoveryError, ExecutionRecoveryExecutor, _snapshot_signature
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
        completion = self.receipts.get(result["completion_receipt_id"])
        self.assertIsNotNone(completion)
        self.assertEqual(completion.outcome, "committed")
        evidence = executor.verify_recovery_evidence()
        self.assertEqual(evidence["status"], "passed")
        self.assertEqual(evidence["chain"]["count"], 1)
        self.assertEqual(executor.recovery_evidence_status()["status"], "passed")
        self.assertTrue(executor.recovery_evidence_status()["claim"])
        status_snapshot = executor.verify_recovery_evidence_status_snapshot()
        self.assertEqual(status_snapshot["status"], "passed")
        replay = executor.handle(self.action, self.context)
        self.assertEqual(replay["status"], "replayed")
        self.assertEqual(replay["recovery_evidence"]["snapshot"]["status"], "passed")
        self.assertEqual(replay["replay_evidence"]["schema_version"], "noesis.recovery-replay-evidence.v1")
        self.assertTrue(replay["replay_evidence"]["claim"])
        audited = executor.audit_replay_outcome(self.action)
        self.assertEqual(audited["action_id"], self.action.action_id)
        self.assertEqual(audited["completion_receipt_id"], replay["replay_evidence"]["completion_receipt_id"])
        inventory_snapshot = executor.verify_replay_snapshot_inventory_snapshot(self.action)
        self.assertEqual(inventory_snapshot["payload"]["schema_version"], "noesis.recovery-replay-snapshot-inventory-snapshot.v1")
        self.assertEqual(replay["replay_inventory_snapshot"]["status"], "passed")
        self.assertEqual(replay["replay_catalog"]["schema_version"], "noesis.recovery-replay-evidence-catalog.v1")
        self.assertEqual(replay["replay_catalog"]["count"], 1)
        catalog_snapshot = executor.verify_replay_evidence_catalog_snapshot()
        self.assertEqual(catalog_snapshot["payload"]["schema_version"], "noesis.recovery-replay-evidence-catalog-snapshot.v1")
        self.assertEqual(replay["replay_catalog_snapshot"]["status"], "passed")
        commit_manifest = executor.verify_replay_evidence_commit_manifest(self.action)
        self.assertEqual(commit_manifest["payload"]["schema_version"], "noesis.recovery-replay-evidence-commit-manifest.v1")
        self.assertEqual(replay["replay_commit_manifest"]["status"], "passed")
        manifest_payload = replay["replay_commit_manifest"]["payload"]
        self.assertEqual(manifest_payload["bundle_digest"], executor._replay_bundle_digest(manifest_payload))
        self.assertEqual(replay["replay_completeness"]["schema_version"], "noesis.recovery-replay-evidence-completeness.v1")
        self.assertEqual(replay["replay_completeness"]["manifest_count"], 1)
        completeness_snapshot = executor.verify_replay_evidence_completeness_snapshot()
        self.assertEqual(completeness_snapshot["payload"]["schema_version"], "noesis.recovery-replay-evidence-completeness-snapshot.v1")
        self.assertEqual(replay["replay_completeness_snapshot"]["status"], "passed")
        self.assertEqual(executor.audit_replay_evidence_catalog()["count"], 1)
        inventory_one = executor.audit_replay_snapshot_inventory(self.action)
        inventory_two = executor.audit_replay_snapshot_inventory(self.action)
        self.assertEqual(inventory_one, inventory_two)
        self.assertEqual(inventory_one["schema_version"], "noesis.recovery-replay-snapshot-inventory.v1")
        self.assertEqual(inventory_one["action_id"], self.action.action_id)

    def test_completion_event_chain_audit_rejects_reorder_and_corruption(self):
        event_path = str(Path(self.tmp.name) / "completion-chain-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        first_replay_path = executor._replay_snapshot_path(self.action.action_id)
        first_inventory_path = executor._replay_inventory_snapshot_path(self.action.action_id)
        snapshot_path = Path(event_path + ".snapshot.json")
        original_snapshot = snapshot_path.read_text(encoding="utf-8")
        self.recovery.begin("run-chain-2", "sha256:before")
        self.recovery.complete("run-chain-2", workspace_after="sha256:after", receipt_id=self.receipt.receipt_id, status="completed")
        action_two = ExecutionRecoveryAction("action-chain-2", "rollback", "run-chain-2", self.receipt.receipt_id, "patch-1", "ws-1", "snap-base", "operator-1", "session-1")
        executor.handle(action_two, self.context)
        self.assertNotEqual(first_replay_path, executor._replay_snapshot_path(action_two.action_id))
        self.assertNotEqual(first_inventory_path, executor._replay_inventory_snapshot_path(action_two.action_id))
        self.assertTrue(Path(first_replay_path).exists())
        self.assertTrue(Path(first_inventory_path).exists())
        self.assertEqual(executor.handle(self.action, self.context)["status"], "replayed")
        replay_two = executor.handle(action_two, self.context)
        self.assertEqual(replay_two["status"], "replayed")
        self.assertEqual(replay_two["replay_catalog"]["count"], 2)
        self.assertEqual(replay_two["replay_catalog_snapshot"]["payload"]["count"], 2)
        self.assertEqual(replay_two["replay_commit_manifest"]["status"], "passed")
        self.assertEqual(replay_two["replay_completeness"]["manifest_count"], 2)
        self.assertEqual(replay_two["replay_completeness_snapshot"]["payload"]["manifest_count"], 2)
        self.assertEqual(executor.verify_replay_evidence_completeness_snapshot()["status"], "passed")
        self.assertEqual(executor.verify_replay_evidence_commit_manifest(action_two)["status"], "passed")
        self.assertEqual(executor.verify_replay_evidence_catalog_snapshot()["status"], "passed")
        self.assertEqual(executor.audit_replay_evidence_catalog()["count"], 2)
        audited = executor.audit_completion_events()
        self.assertEqual(audited["status"], "passed")
        self.assertEqual(audited["count"], 2)
        snapshot = executor.verify_completion_event_snapshot()
        self.assertEqual(snapshot["status"], "passed")
        original_events = Path(event_path).read_text(encoding="utf-8")
        records = [json.loads(line) for line in original_events.splitlines() if line.strip()]
        records.reverse()
        Path(event_path).write_text("\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "chain_mismatch"):
            ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True).audit_completion_events()

        Path(event_path).write_text(original_events, encoding="utf-8")
        snapshot_path.write_text(original_snapshot, encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "event_snapshot_drift"):
            ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True).verify_completion_event_snapshot()
        tampered = json.loads(original_snapshot)
        tampered["payload"]["chain_digest"] = "sha256:tampered"
        snapshot_path.write_text(json.dumps(tampered, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "event_snapshot_signature_invalid"):
            ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True).verify_completion_event_snapshot()

    def test_recovery_evidence_status_preserves_not_run_and_blocked(self):
        empty_path = str(Path(self.tmp.name) / "empty-status-events.jsonl")
        empty = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=empty_path, rollback_handler=lambda _: True)
        self.assertEqual(empty.recovery_evidence_status()["status"], "not_run")
        self.assertFalse(empty.recovery_evidence_status()["claim"])
        event_path = str(Path(self.tmp.name) / "blocked-status-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        Path(event_path + ".snapshot.json").unlink()
        blocked = executor.recovery_evidence_status()
        self.assertEqual(blocked["status"], "blocked")
        self.assertFalse(blocked["claim"])
        self.assertEqual(blocked["reason"], "recovery_event_snapshot_missing")

    def test_status_snapshot_rejects_tamper_and_projection_drift(self):
        event_path = str(Path(self.tmp.name) / "status-snapshot-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        snapshot_path = Path(event_path + ".status.json")
        original = snapshot_path.read_text(encoding="utf-8")
        tampered = json.loads(original)
        tampered["payload"]["claim"] = False
        snapshot_path.write_text(json.dumps(tampered, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "status_snapshot_signature_invalid"):
            executor.verify_recovery_evidence_status_snapshot()
        snapshot_path.write_text(original, encoding="utf-8")
        Path(event_path + ".snapshot.json").unlink()
        with self.assertRaisesRegex(ExecutionRecoveryError, "status_snapshot_drift"):
            executor.verify_recovery_evidence_status_snapshot()
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_event_snapshot_missing"):
            executor.handle(self.action, self.context)

    def test_replay_requires_completion_event_snapshot(self):
        event_path = str(Path(self.tmp.name) / "replay-event-snapshot-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        Path(executor._completion_snapshot_path()).unlink()
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_event_snapshot_missing"):
            executor.handle(self.action, self.context)

    def test_replay_rejects_completion_event_snapshot_drift(self):
        event_path = str(Path(self.tmp.name) / "replay-event-snapshot-drift-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        snapshot_path = Path(executor._completion_snapshot_path())
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot["payload"]["chain_digest"] = "sha256:drift"
        snapshot["signature"] = _snapshot_signature(snapshot["payload"], self.key)
        snapshot_path.write_text(json.dumps(snapshot, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_event_snapshot_drift"):
            executor.handle(self.action, self.context)

    def test_replay_requires_status_snapshot(self):
        event_path = str(Path(self.tmp.name) / "replay-status-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        Path(executor._status_snapshot_path(self.action.action_id)).unlink()
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_status_snapshot_missing"):
            executor.handle(self.action, self.context)

    def test_replay_requires_replay_outcome_snapshot(self):
        event_path = str(Path(self.tmp.name) / "replay-outcome-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        Path(executor._replay_snapshot_path(self.action.action_id)).unlink()
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_snapshot_missing"):
            executor.handle(self.action, self.context)

    def test_replay_outcome_snapshot_rejects_tampering(self):
        event_path = str(Path(self.tmp.name) / "tampered-replay-outcome-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        snapshot_path = Path(executor._replay_snapshot_path(self.action.action_id))
        tampered = json.loads(snapshot_path.read_text(encoding="utf-8"))
        tampered["payload"]["claim"] = False
        snapshot_path.write_text(json.dumps(tampered, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_snapshot_signature_invalid"):
            executor.handle(self.action, self.context)

    def test_replay_inventory_snapshot_missing_blocks_exact_replay(self):
        event_path = str(Path(self.tmp.name) / "missing-inventory-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        Path(executor._replay_inventory_snapshot_path(self.action.action_id)).unlink()
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_inventory_snapshot_missing"):
            executor.handle(self.action, self.context)

    def test_replay_inventory_snapshot_rejects_signed_path_mismatch(self):
        event_path = str(Path(self.tmp.name) / "inventory-path-mismatch-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        snapshot_path = Path(executor._replay_inventory_snapshot_path(self.action.action_id))
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot["payload"]["inventory_path"] = str(Path(self.tmp.name) / "other-inventory.json")
        snapshot["signature"] = _snapshot_signature(snapshot["payload"], self.key)
        snapshot_path.write_text(json.dumps(snapshot, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_inventory_snapshot_path_mismatch"):
            executor.handle(self.action, self.context)

    def test_replay_inventory_snapshot_rejects_signed_drift(self):
        event_path = str(Path(self.tmp.name) / "inventory-drift-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        snapshot_path = Path(executor._replay_inventory_snapshot_path(self.action.action_id))
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot["payload"]["snapshot_digest"] = "sha256:drift"
        snapshot["signature"] = _snapshot_signature(snapshot["payload"], self.key)
        snapshot_path.write_text(json.dumps(snapshot, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_inventory_snapshot_drift"):
            executor.verify_replay_snapshot_inventory_snapshot(self.action)

    def test_replay_snapshot_rejects_signed_path_mismatch(self):
        event_path = str(Path(self.tmp.name) / "path-mismatch-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        snapshot_path = Path(executor._replay_snapshot_path(self.action.action_id))
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot["payload"]["snapshot_path"] = str(Path(self.tmp.name) / "other-replay.json")
        snapshot["signature"] = _snapshot_signature(snapshot["payload"], self.key)
        snapshot_path.write_text(json.dumps(snapshot, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_snapshot_path_mismatch"):
            executor.audit_replay_snapshot_inventory(self.action)

    def test_replay_snapshot_rejects_signed_action_identity_confusion(self):
        event_path = str(Path(self.tmp.name) / "identity-confusion-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        snapshot_path = Path(executor._replay_snapshot_path(self.action.action_id))
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot["payload"]["action_id"] = "action-confused"
        snapshot["signature"] = _snapshot_signature(snapshot["payload"], self.key)
        snapshot_path.write_text(json.dumps(snapshot, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_snapshot_identity_conflict"):
            executor.audit_replay_snapshot_inventory(self.action)

    def test_replay_completeness_snapshot_missing_blocks_exact_replay(self):
        event_path = str(Path(self.tmp.name) / "missing-completeness-snapshot-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        Path(executor._replay_completeness_snapshot_path()).unlink()
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_completeness_snapshot_missing"):
            executor.handle(self.action, self.context)

    def test_replay_completeness_snapshot_rejects_signed_path_mismatch(self):
        event_path = str(Path(self.tmp.name) / "completeness-path-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        snapshot_path = Path(executor._replay_completeness_snapshot_path())
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot["payload"]["completeness_path"] = str(Path(self.tmp.name) / "other-completeness.json")
        snapshot["signature"] = _snapshot_signature(snapshot["payload"], self.key)
        snapshot_path.write_text(json.dumps(snapshot, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_completeness_snapshot_path_mismatch"):
            executor.handle(self.action, self.context)

    def test_replay_completeness_snapshot_rejects_signed_drift(self):
        event_path = str(Path(self.tmp.name) / "completeness-drift-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        snapshot_path = Path(executor._replay_completeness_snapshot_path())
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot["payload"]["completeness_digest"] = "sha256:drift"
        snapshot["signature"] = _snapshot_signature(snapshot["payload"], self.key)
        snapshot_path.write_text(json.dumps(snapshot, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_completeness_snapshot_drift"):
            executor.verify_replay_evidence_completeness_snapshot()

    def test_replay_completeness_rejects_sidecar_signature(self):
        event_path = str(Path(self.tmp.name) / "sidecar-signature-completeness-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        snapshot_path = Path(executor._replay_snapshot_path(self.action.action_id))
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot["signature"] = "sha256:tampered"
        snapshot_path.write_text(json.dumps(snapshot, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_completeness_sidecar_signature_invalid"):
            executor.audit_replay_evidence_completeness()

    def test_replay_completeness_rejects_missing_bundle_path(self):
        event_path = str(Path(self.tmp.name) / "missing-bundle-path-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        Path(executor._replay_snapshot_path(self.action.action_id)).unlink()
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_completeness_bundle_path_missing"):
            executor.audit_replay_evidence_completeness()

    def test_replay_completeness_rejects_bundle_digest_mismatch(self):
        event_path = str(Path(self.tmp.name) / "bundle-digest-completeness-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        manifest_path = Path(executor._replay_commit_manifest_path(self.action.action_id))
        snapshot = json.loads(manifest_path.read_text(encoding="utf-8"))
        snapshot["payload"]["bundle_digest"] = "sha256:tampered"
        snapshot["signature"] = _snapshot_signature(snapshot["payload"], self.key)
        manifest_path.write_text(json.dumps(snapshot, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_completeness_bundle_digest_mismatch"):
            executor.audit_replay_evidence_completeness()

    def test_replay_completeness_rejects_missing_manifest(self):
        event_path = str(Path(self.tmp.name) / "missing-completeness-manifest-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        Path(executor._replay_commit_manifest_path(self.action.action_id)).unlink()
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_completeness_manifest_missing"):
            executor.audit_replay_evidence_completeness()

    def test_replay_commit_manifest_missing_blocks_exact_replay(self):
        event_path = str(Path(self.tmp.name) / "missing-commit-manifest-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        Path(executor._replay_commit_manifest_path(self.action.action_id)).unlink()
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_commit_manifest_missing"):
            executor.handle(self.action, self.context)

    def test_replay_commit_manifest_rejects_signed_path_mismatch(self):
        event_path = str(Path(self.tmp.name) / "commit-manifest-path-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        snapshot_path = Path(executor._replay_commit_manifest_path(self.action.action_id))
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot["payload"]["catalog_snapshot_path"] = str(Path(self.tmp.name) / "other-catalog.json")
        snapshot["signature"] = _snapshot_signature(snapshot["payload"], self.key)
        snapshot_path.write_text(json.dumps(snapshot, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_commit_manifest_path_mismatch"):
            executor.handle(self.action, self.context)

    def test_replay_commit_manifest_rejects_signed_drift(self):
        event_path = str(Path(self.tmp.name) / "commit-manifest-drift-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        snapshot_path = Path(executor._replay_commit_manifest_path(self.action.action_id))
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot["payload"]["catalog_record_digest"] = "sha256:drift"
        snapshot["signature"] = _snapshot_signature(snapshot["payload"], self.key)
        snapshot_path.write_text(json.dumps(snapshot, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_commit_manifest_drift"):
            executor.verify_replay_evidence_commit_manifest(self.action)

    def test_replay_catalog_snapshot_missing_blocks_exact_replay(self):
        event_path = str(Path(self.tmp.name) / "missing-catalog-snapshot-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        Path(executor._replay_catalog_snapshot_path()).unlink()
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_catalog_snapshot_missing"):
            executor.handle(self.action, self.context)

    def test_replay_catalog_snapshot_rejects_signed_path_mismatch(self):
        event_path = str(Path(self.tmp.name) / "catalog-path-mismatch-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        snapshot_path = Path(executor._replay_catalog_snapshot_path())
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot["payload"]["catalog_path"] = str(Path(self.tmp.name) / "other-catalog.json")
        snapshot["signature"] = _snapshot_signature(snapshot["payload"], self.key)
        snapshot_path.write_text(json.dumps(snapshot, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_catalog_snapshot_path_mismatch"):
            executor.handle(self.action, self.context)

    def test_replay_catalog_snapshot_rejects_signed_drift(self):
        event_path = str(Path(self.tmp.name) / "catalog-drift-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        snapshot_path = Path(executor._replay_catalog_snapshot_path())
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot["payload"]["catalog_digest"] = "sha256:drift"
        snapshot["signature"] = _snapshot_signature(snapshot["payload"], self.key)
        snapshot_path.write_text(json.dumps(snapshot, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_catalog_snapshot_drift"):
            executor.verify_replay_evidence_catalog_snapshot()

    def test_replay_catalog_rejects_duplicate_action_records(self):
        event_path = str(Path(self.tmp.name) / "duplicate-catalog-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        original_path = Path(executor._replay_inventory_snapshot_path(self.action.action_id))
        duplicate_path = Path(str(original_path).replace(".inventory.json", ".zzz.json.inventory.json"))
        duplicate = json.loads(original_path.read_text(encoding="utf-8"))
        duplicate["payload"]["inventory_path"] = str(duplicate_path)
        duplicate["signature"] = _snapshot_signature(duplicate["payload"], self.key)
        duplicate_path.write_text(json.dumps(duplicate, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_catalog_duplicate_action"):
            executor.audit_replay_evidence_catalog()

    def test_replay_snapshot_rejects_duplicate_record_keys(self):
        event_path = str(Path(self.tmp.name) / "duplicate-record-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        snapshot_path = Path(executor._replay_snapshot_path(self.action.action_id))
        original = snapshot_path.read_text(encoding="utf-8").strip()
        duplicate = original[:-1] + ',"payload":{"action_id":"conflicting"}}'
        snapshot_path.write_text(duplicate + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_snapshot_duplicate_record"):
            executor.audit_replay_snapshot_inventory(self.action)

    def test_startup_evidence_gate_rejects_missing_snapshot(self):
        event_path = str(Path(self.tmp.name) / "missing-snapshot-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        Path(event_path + ".snapshot.json").unlink()
        with self.assertRaisesRegex(ExecutionRecoveryError, "event_snapshot_missing"):
            ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True).verify_recovery_evidence()

    def test_replay_rejects_tampered_completion_receipt_reference(self):
        event_path = str(Path(self.tmp.name) / "tampered-completion-events.jsonl")
        self.recovery.begin("run-tamper", "sha256:before")
        self.recovery.complete("run-tamper", workspace_after="sha256:after", receipt_id=self.receipt.receipt_id, status="completed")
        action = ExecutionRecoveryAction("action-tamper", "rollback", "run-tamper", self.receipt.receipt_id, "patch-1", "ws-1", "snap-base", "operator-1", "session-1")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(action, self.context)
        records = [json.loads(line) for line in Path(event_path).read_text(encoding="utf-8").splitlines() if line.strip()]
        records[0]["payload"]["completion_receipt_id"] = "receipt:missing"
        Path(event_path).write_text("\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "completion_receipt_invalid"):
            executor.handle(action, self.context)

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

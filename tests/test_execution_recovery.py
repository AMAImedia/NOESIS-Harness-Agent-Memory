import tempfile
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from noesis_harness.execution_assurance import ExecutionReceiptStore, ExecutionRecoveryStore, create_receipt, request_fingerprint
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
        verifier = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        with self.assertRaisesRegex(ExecutionRecoveryError, "chain_mismatch"):
            verifier.audit_completion_events()
        with self.assertRaisesRegex(ExecutionRecoveryError, "chain_mismatch"):
            verifier.verify_replay_generation_receipt()

        duplicate_records = [json.loads(line) for line in original_events.splitlines() if line.strip()]
        duplicate_records.append(duplicate_records[-1])
        Path(event_path).write_text("\n".join(json.dumps(record, sort_keys=True) for record in duplicate_records) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "completion_event_fork"):
            verifier.verify_replay_generation_receipt()

        Path(event_path).write_text(original_events, encoding="utf-8")
        self.assertEqual(verifier.verify_replay_generation_receipt()["status"], "passed")
        snapshot_path.write_text(original_snapshot, encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "event_snapshot_drift"):
            ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True).verify_completion_event_snapshot()
        tampered = json.loads(original_snapshot)
        tampered["payload"]["chain_digest"] = "sha256:tampered"
        snapshot_path.write_text(json.dumps(tampered, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "event_snapshot_signature_invalid"):
            ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True).verify_completion_event_snapshot()

    def test_completion_snapshot_schema_rotation_and_process_boundary(self):
        event_path = str(Path(self.tmp.name) / "event-snapshot-schema-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        snapshot_path = Path(executor._completion_snapshot_path())
        original = snapshot_path.read_bytes()
        cases = (("unknown", lambda payload: payload.update({"unknown": "fixture"}), "recovery_event_snapshot_unknown_field"), ("missing", lambda payload: payload.pop("event_ids"), "recovery_event_snapshot_missing_field"), ("schema", lambda payload: payload.update({"schema_version": "noesis.recovery-event-chain-snapshot.v0"}), "recovery_event_snapshot_schema_invalid"), ("shape", lambda payload: payload.update({"count": 99}), "recovery_event_snapshot_shape_invalid"))
        for _, mutate, reason in cases:
            tampered = json.loads(original)
            mutate(tampered["payload"])
            tampered["signature"] = _snapshot_signature(tampered["payload"], self.key)
            snapshot_path.write_text(json.dumps(tampered, sort_keys=True) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ExecutionRecoveryError, reason):
                executor.verify_completion_event_snapshot()
            snapshot_path.write_bytes(original)
        snapshot_path.write_text('{"payload":{"schema_version":"x","schema_version":"y"},"signature":"x"}\n', encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_event_snapshot_duplicate_record"):
            executor.verify_completion_event_snapshot()
        snapshot_path.write_bytes(original)
        root = Path(__file__).resolve().parents[1]
        child = """import sys
from noesis_harness.execution_assurance import ExecutionReceiptStore, ExecutionRecoveryStore
from noesis_harness.execution_recovery import ExecutionRecoveryExecutor
from noesis_harness.workspaces import PatchReviewStore
root, event_path = sys.argv[1], sys.argv[2]
key = b'execution-recovery-signing-key'
executor = ExecutionRecoveryExecutor(receipt_store=ExecutionReceiptStore(root + '/receipts.db', signing_key=key), recovery_store=ExecutionRecoveryStore(root + '/recovery.db'), patch_store=PatchReviewStore(root + '/patches.db'), event_path=event_path, rollback_handler=lambda _: True)
print(executor.verify_completion_event_snapshot()['status'])
"""
        env = dict(os.environ)
        env["PYTHONPATH"] = str(root)
        process = subprocess.run([sys.executable, "-c", child, str(self.tmp.name), event_path], capture_output=True, text=True, check=True, env=env)
        self.assertEqual(process.stdout.strip(), "passed")
        self.assertEqual(process.stderr, "")
        snapshot_path.unlink()
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_event_snapshot_missing"):
            executor.verify_completion_event_snapshot()

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

    def test_startup_completeness_audit_requires_durable_snapshot(self):
        event_path = str(Path(self.tmp.name) / "required-completeness-snapshot-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        Path(executor._replay_completeness_snapshot_path()).unlink()
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_completeness_snapshot_required"):
            executor.audit_replay_evidence_completeness(require_durable_snapshot=True)

    def test_startup_completeness_audit_rejects_signed_digest_drift(self):
        event_path = str(Path(self.tmp.name) / "startup-completeness-digest-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        snapshot_path = Path(executor._replay_completeness_snapshot_path())
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot["payload"]["completeness_digest"] = "sha256:stale-startup-digest"
        snapshot["signature"] = _snapshot_signature(snapshot["payload"], self.key)
        snapshot_path.write_text(json.dumps(snapshot, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_completeness_snapshot_drift"):
            executor.audit_replay_evidence_completeness(require_durable_snapshot=True)

    def test_completeness_snapshot_rejects_schema_status_and_count_shape(self):
        event_path = str(Path(self.tmp.name) / "completeness-schema-shape-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        snapshot_path = Path(executor._replay_completeness_snapshot_path())
        original = json.loads(snapshot_path.read_text(encoding="utf-8"))
        for field, value, reason in (("schema_version", "noesis.invalid.v1", "recovery_replay_completeness_snapshot_schema_invalid"), ("status", "not_run", "recovery_replay_completeness_snapshot_status_invalid"), ("manifest_count", True, "recovery_replay_completeness_snapshot_counts_invalid")):
            snapshot = json.loads(json.dumps(original))
            snapshot["payload"][field] = value
            snapshot["signature"] = _snapshot_signature(snapshot["payload"], self.key)
            snapshot_path.write_text(json.dumps(snapshot, sort_keys=True) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ExecutionRecoveryError, reason):
                executor.verify_replay_evidence_completeness_snapshot()

    def test_completeness_snapshot_rejects_invalid_records_and_duplicate_action_ids(self):
        event_path = str(Path(self.tmp.name) / "completeness-record-shape-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        snapshot_path = Path(executor._replay_completeness_snapshot_path())
        original = json.loads(snapshot_path.read_text(encoding="utf-8"))
        invalid_records = json.loads(json.dumps(original))
        invalid_records["payload"]["records"] = {"action_id": "action-1"}
        invalid_records["signature"] = _snapshot_signature(invalid_records["payload"], self.key)
        snapshot_path.write_text(json.dumps(invalid_records, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_completeness_snapshot_records_invalid"):
            executor.verify_replay_evidence_completeness_snapshot()
        duplicate_records = json.loads(json.dumps(original))
        duplicate_records["payload"]["records"] = duplicate_records["payload"]["records"] * 2
        duplicate_records["payload"]["manifest_count"] = 2
        duplicate_records["signature"] = _snapshot_signature(duplicate_records["payload"], self.key)
        snapshot_path.write_text(json.dumps(duplicate_records, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_completeness_snapshot_duplicate_action"):
            executor.verify_replay_evidence_completeness_snapshot()

    def test_completeness_snapshot_rejects_duplicate_json_keys(self):
        event_path = str(Path(self.tmp.name) / "completeness-duplicate-keys-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        snapshot_path = Path(executor._replay_completeness_snapshot_path())
        snapshot_path.write_text('{"payload": {"schema_version": "x", "schema_version": "y"}, "signature": "x"}\n', encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_completeness_snapshot_duplicate_record"):
            executor.verify_replay_evidence_completeness_snapshot()

    def test_completeness_snapshot_rejects_unknown_and_missing_canonical_fields(self):
        event_path = str(Path(self.tmp.name) / "completeness-canonical-fields-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        snapshot_path = Path(executor._replay_completeness_snapshot_path())
        original = json.loads(snapshot_path.read_text(encoding="utf-8"))
        unknown = json.loads(json.dumps(original))
        unknown["payload"]["unexpected_field"] = "drift"
        unknown["signature"] = _snapshot_signature(unknown["payload"], self.key)
        snapshot_path.write_text(json.dumps(unknown, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_completeness_snapshot_unknown_field"):
            executor.verify_replay_evidence_completeness_snapshot()
        missing = json.loads(json.dumps(original))
        del missing["payload"]["records"]
        missing["signature"] = _snapshot_signature(missing["payload"], self.key)
        snapshot_path.write_text(json.dumps(missing, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_completeness_snapshot_missing_field"):
            executor.verify_replay_evidence_completeness_snapshot()

    def test_completeness_snapshot_rejects_unknown_record_field(self):
        event_path = str(Path(self.tmp.name) / "completeness-record-canonical-fields-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        snapshot_path = Path(executor._replay_completeness_snapshot_path())
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot["payload"]["records"][0]["unexpected_field"] = "drift"
        snapshot["signature"] = _snapshot_signature(snapshot["payload"], self.key)
        snapshot_path.write_text(json.dumps(snapshot, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_completeness_snapshot_record_schema_invalid"):
            executor.verify_replay_evidence_completeness_snapshot()

    def test_completeness_snapshot_rewrite_is_byte_identical_and_reopenable(self):
        event_path = str(Path(self.tmp.name) / "completeness-byte-identity-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        snapshot_path = Path(executor._replay_completeness_snapshot_path())
        first_bytes = snapshot_path.read_bytes()
        first_snapshot = executor.persist_replay_evidence_completeness()
        second_bytes = snapshot_path.read_bytes()
        second_snapshot = executor.persist_replay_evidence_completeness()
        third_bytes = snapshot_path.read_bytes()
        self.assertEqual(first_bytes, second_bytes)
        self.assertEqual(second_bytes, third_bytes)
        self.assertEqual(first_snapshot, second_snapshot)
        reopened = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        self.assertEqual(reopened.verify_replay_evidence_completeness_snapshot()["status"], "passed")

    def test_completeness_snapshot_reopens_across_python_process_boundary(self):
        event_path = str(Path(self.tmp.name) / "completeness-process-boundary-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        root = Path(__file__).resolve().parents[1]
        child = """import sys\nfrom noesis_harness.execution_assurance import ExecutionReceiptStore, ExecutionRecoveryStore\nfrom noesis_harness.execution_recovery import ExecutionRecoveryExecutor\nroot, event_path = sys.argv[1], sys.argv[2]\nkey = b\"execution-recovery-signing-key\"\nexecutor = ExecutionRecoveryExecutor(receipt_store=ExecutionReceiptStore(root + \"/receipts.db\", signing_key=key), recovery_store=ExecutionRecoveryStore(root + \"/recovery.db\"), patch_store=__import__(\"noesis_harness.workspaces\", fromlist=[\"PatchReviewStore\"]).PatchReviewStore(root + \"/patches.db\"), event_path=event_path, rollback_handler=lambda _: True)\nprint(executor.verify_replay_evidence_completeness_snapshot()[\"status\"])\n"""
        env = dict(os.environ)
        env["PYTHONPATH"] = str(root)
        completed = subprocess.run([sys.executable, "-c", child, self.tmp.name, event_path], capture_output=True, text=True, env=env, check=True)
        self.assertEqual(completed.stdout.strip(), "passed")
        self.assertEqual(completed.stderr, "")

    def test_completeness_snapshot_replace_interruption_preserves_previous_valid_snapshot(self):
        event_path = str(Path(self.tmp.name) / "completeness-replace-interruption-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        snapshot_path = Path(executor._replay_completeness_snapshot_path())
        previous_bytes = snapshot_path.read_bytes()
        with patch("noesis_harness.execution_recovery.os.replace", side_effect=OSError("simulated_process_interruption")):
            with self.assertRaisesRegex(OSError, "simulated_process_interruption"):
                executor.persist_replay_evidence_completeness()
        self.assertEqual(snapshot_path.read_bytes(), previous_bytes)
        self.assertEqual(executor.verify_replay_evidence_completeness_snapshot()["status"], "passed")
        self.assertEqual(list(snapshot_path.parent.glob(".recovery-chain-*.tmp")), [])

    def test_completeness_snapshot_ignores_orphan_partial_temporary_file(self):
        event_path = str(Path(self.tmp.name) / "completeness-partial-temp-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        snapshot_path = Path(executor._replay_completeness_snapshot_path())
        partial_path = snapshot_path.parent / ".recovery-chain-crashed.tmp"
        partial_path.write_text('{"payload": {"status": "passed"}', encoding="utf-8")
        self.assertEqual(executor.verify_replay_evidence_completeness_snapshot()["status"], "passed")
        snapshot_path.unlink()
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_completeness_snapshot_missing"):
            executor.verify_replay_evidence_completeness_snapshot()
        self.assertTrue(partial_path.exists())

    def test_multi_action_snapshot_stale_after_crash_then_finalizes_full_catalog(self):
        event_path = str(Path(self.tmp.name) / "completeness-multi-action-crash-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        self.recovery.begin("run-2", "sha256:before")
        self.recovery.complete("run-2", workspace_after="sha256:after", receipt_id=self.receipt.receipt_id, status="completed")
        proposal = PatchProposal("patch-2", "ws-1", "snap-base", "snap-head", ({"path": "out-2.txt", "kind": "modified"},), "approved")
        self.patches.put(proposal)
        action_two = ExecutionRecoveryAction("action-2", "rollback", "run-2", self.receipt.receipt_id, "patch-2", "ws-1", "snap-base", "operator-1", "session-1")
        with patch.object(executor, "persist_replay_evidence_completeness", side_effect=OSError("simulated_crash_before_snapshot_update")):
            with self.assertRaisesRegex(OSError, "simulated_crash_before_snapshot_update"):
                executor.handle(action_two, self.context)
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_completeness_snapshot_drift"):
            executor.verify_replay_evidence_completeness_snapshot()
        final_snapshot = executor.persist_replay_evidence_completeness()
        executor.persist_replay_evidence_commit_manifest(action_two)
        self.assertEqual(final_snapshot["payload"]["manifest_count"], 2)
        self.assertEqual(final_snapshot["payload"]["catalog_count"], 2)
        stable_bytes = Path(executor._replay_completeness_snapshot_path()).read_bytes()
        executor.persist_replay_evidence_completeness()
        self.assertEqual(Path(executor._replay_completeness_snapshot_path()).read_bytes(), stable_bytes)
        self.assertEqual(executor.handle(action_two, self.context)["status"], "replayed")

    def test_multi_action_corrupted_manifest_blocks_bundle_then_explicit_rebuild_passes(self):
        event_path = str(Path(self.tmp.name) / "completeness-manifest-corruption-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        self.recovery.begin("run-corrupt-2", "sha256:before")
        self.recovery.complete("run-corrupt-2", workspace_after="sha256:after", receipt_id=self.receipt.receipt_id, status="completed")
        proposal = PatchProposal("patch-corrupt-2", "ws-1", "snap-base", "snap-head", ({"path": "out-corrupt-2.txt", "kind": "modified"},), "approved")
        self.patches.put(proposal)
        action_two = ExecutionRecoveryAction("action-corrupt-2", "rollback", "run-corrupt-2", self.receipt.receipt_id, "patch-corrupt-2", "ws-1", "snap-base", "operator-1", "session-1")
        executor.handle(action_two, self.context)
        manifest_path = Path(executor._replay_commit_manifest_path(action_two.action_id))
        original_manifest = manifest_path.read_bytes()
        corrupted = json.loads(original_manifest)
        corrupted["payload"]["action_digest"] = "sha256:signed-but-wrong-action"
        corrupted["payload"]["bundle_digest"] = executor._replay_bundle_digest(corrupted["payload"])
        corrupted["signature"] = _snapshot_signature(corrupted["payload"], self.key)
        manifest_path.write_text(json.dumps(corrupted, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_completeness_identity_conflict"):
            executor.audit_replay_evidence_completeness(require_durable_snapshot=True)
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_commit_manifest_drift"):
            executor.verify_replay_evidence_commit_manifest(action_two)
        manifest_path.write_bytes(original_manifest)
        self.assertEqual(executor.audit_replay_evidence_completeness(require_durable_snapshot=True)["manifest_count"], 2)
        rebuilt = executor.persist_replay_evidence_commit_manifest(action_two)
        self.assertEqual(rebuilt["payload"]["action_id"], action_two.action_id)
        repaired_bytes = manifest_path.read_bytes()
        executor.persist_replay_evidence_commit_manifest(action_two)
        self.assertEqual(manifest_path.read_bytes(), repaired_bytes)
        self.assertEqual(executor.audit_replay_evidence_completeness(require_durable_snapshot=True)["manifest_count"], 2)
        self.assertEqual(executor.verify_replay_evidence_commit_manifest(action_two)["status"], "passed")

    def test_multi_action_corrupted_catalog_blocks_bundle_then_restores_deterministically(self):
        event_path = str(Path(self.tmp.name) / "completeness-catalog-corruption-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        self.recovery.begin("run-catalog-2", "sha256:before")
        self.recovery.complete("run-catalog-2", workspace_after="sha256:after", receipt_id=self.receipt.receipt_id, status="completed")
        proposal = PatchProposal("patch-catalog-2", "ws-1", "snap-base", "snap-head", ({"path": "out-catalog-2.txt", "kind": "modified"},), "approved")
        self.patches.put(proposal)
        action_two = ExecutionRecoveryAction("action-catalog-2", "rollback", "run-catalog-2", self.receipt.receipt_id, "patch-catalog-2", "ws-1", "snap-base", "operator-1", "session-1")
        executor.handle(action_two, self.context)
        catalog_path = Path(executor._replay_catalog_snapshot_path())
        original_catalog = catalog_path.read_bytes()
        corrupted = json.loads(original_catalog)
        corrupted["payload"]["records"].append({"action_id": "catalog-untrusted-extra"})
        corrupted["payload"]["count"] = len(corrupted["payload"]["records"])
        corrupted["payload"]["catalog_digest"] = executor.audit_replay_evidence_catalog()["catalog_digest"]
        corrupted["signature"] = _snapshot_signature(corrupted["payload"], self.key)
        catalog_path.write_text(json.dumps(corrupted, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_catalog_snapshot_drift"):
            executor.audit_replay_evidence_completeness(require_durable_snapshot=True)
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_catalog_snapshot_drift"):
            executor.verify_replay_evidence_catalog_snapshot()
        catalog_path.write_bytes(original_catalog)
        self.assertEqual(executor.verify_replay_evidence_catalog_snapshot()["status"], "passed")
        rebuilt = executor.persist_replay_evidence_catalog()
        self.assertEqual(rebuilt["payload"]["count"], 2)
        repaired_bytes = catalog_path.read_bytes()
        executor.persist_replay_evidence_catalog()
        self.assertEqual(catalog_path.read_bytes(), repaired_bytes)
        self.assertEqual(executor.audit_replay_evidence_completeness(require_durable_snapshot=True)["catalog_count"], 2)
        self.assertEqual(executor.verify_replay_evidence_completeness_snapshot()["status"], "passed")

    def test_catalog_record_digest_substitution_blocks_signed_manifest_then_restores(self):
        event_path = str(Path(self.tmp.name) / "completeness-record-binding-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        self.recovery.begin("run-record-binding-2", "sha256:before")
        self.recovery.complete("run-record-binding-2", workspace_after="sha256:after", receipt_id=self.receipt.receipt_id, status="completed")
        proposal = PatchProposal("patch-record-binding-2", "ws-1", "snap-base", "snap-head", ({"path": "out-record-binding-2.txt", "kind": "modified"},), "approved")
        self.patches.put(proposal)
        action_two = ExecutionRecoveryAction("action-record-binding-2", "rollback", "run-record-binding-2", self.receipt.receipt_id, "patch-record-binding-2", "ws-1", "snap-base", "operator-1", "session-1")
        executor.handle(action_two, self.context)
        catalog = executor.verify_replay_evidence_catalog_snapshot()["payload"]["records"]
        first_record = next(record for record in catalog if record["action_id"] == self.action.action_id)
        manifest_path = Path(executor._replay_commit_manifest_path(action_two.action_id))
        original_manifest = manifest_path.read_bytes()
        corrupted = json.loads(original_manifest)
        corrupted["payload"]["catalog_record_digest"] = request_fingerprint(first_record)
        corrupted["payload"]["bundle_digest"] = executor._replay_bundle_digest(corrupted["payload"])
        corrupted["signature"] = _snapshot_signature(corrupted["payload"], self.key)
        manifest_path.write_text(json.dumps(corrupted, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_completeness_catalog_record_mismatch"):
            executor.audit_replay_evidence_completeness(require_durable_snapshot=True)
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_commit_manifest_drift"):
            executor.verify_replay_evidence_commit_manifest(action_two)
        manifest_path.write_bytes(original_manifest)
        self.assertEqual(executor.audit_replay_evidence_completeness(require_durable_snapshot=True)["manifest_count"], 2)
        executor.persist_replay_evidence_commit_manifest(action_two)
        repaired_bytes = manifest_path.read_bytes()
        executor.persist_replay_evidence_commit_manifest(action_two)
        self.assertEqual(manifest_path.read_bytes(), repaired_bytes)
        self.assertEqual(executor.verify_replay_evidence_commit_manifest(action_two)["status"], "passed")

    def test_duplicate_catalog_and_completeness_action_ids_fail_before_count_parity(self):
        event_path = str(Path(self.tmp.name) / "completeness-duplicate-identities-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        self.recovery.begin("run-duplicate-2", "sha256:before")
        self.recovery.complete("run-duplicate-2", workspace_after="sha256:after", receipt_id=self.receipt.receipt_id, status="completed")
        proposal = PatchProposal("patch-duplicate-2", "ws-1", "snap-base", "snap-head", ({"path": "out-duplicate-2.txt", "kind": "modified"},), "approved")
        self.patches.put(proposal)
        action_two = ExecutionRecoveryAction("action-duplicate-2", "rollback", "run-duplicate-2", self.receipt.receipt_id, "patch-duplicate-2", "ws-1", "snap-base", "operator-1", "session-1")
        executor.handle(action_two, self.context)
        catalog_path = Path(executor._replay_catalog_snapshot_path())
        original_catalog = catalog_path.read_bytes()
        catalog_snapshot = json.loads(original_catalog)
        catalog_snapshot["payload"]["records"].append(dict(catalog_snapshot["payload"]["records"][0]))
        catalog_snapshot["payload"]["count"] = 3
        catalog_snapshot["payload"]["catalog_digest"] = request_fingerprint({"records": catalog_snapshot["payload"]["records"]})
        catalog_snapshot["signature"] = _snapshot_signature(catalog_snapshot["payload"], self.key)
        catalog_path.write_text(json.dumps(catalog_snapshot, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_catalog_snapshot_duplicate_action"):
            executor.verify_replay_evidence_catalog_snapshot()
        catalog_path.write_bytes(original_catalog)
        self.assertEqual(executor.verify_replay_evidence_catalog_snapshot()["status"], "passed")
        completeness_path = Path(executor._replay_completeness_snapshot_path())
        original_completeness = completeness_path.read_bytes()
        completeness_snapshot = json.loads(original_completeness)
        completeness_snapshot["payload"]["records"].append(dict(completeness_snapshot["payload"]["records"][0]))
        completeness_snapshot["payload"]["manifest_count"] = 3
        completeness_snapshot["payload"]["completeness_digest"] = request_fingerprint({"records": completeness_snapshot["payload"]["records"], "catalog_digest": executor.audit_replay_evidence_catalog()["catalog_digest"]})
        completeness_snapshot["signature"] = _snapshot_signature(completeness_snapshot["payload"], self.key)
        completeness_path.write_text(json.dumps(completeness_snapshot, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_completeness_snapshot_duplicate_action"):
            executor.verify_replay_evidence_completeness_snapshot()
        completeness_path.write_bytes(original_completeness)
        self.assertEqual(executor.audit_replay_evidence_completeness(require_durable_snapshot=True)["manifest_count"], 2)
        stable_catalog = catalog_path.read_bytes()
        executor.persist_replay_evidence_catalog()
        self.assertEqual(catalog_path.read_bytes(), stable_catalog)
        stable_completeness = completeness_path.read_bytes()
        executor.persist_replay_evidence_completeness()
        self.assertEqual(completeness_path.read_bytes(), stable_completeness)

    def test_startup_completeness_rejects_orphan_manifest_before_parsing(self):
        event_path = str(Path(self.tmp.name) / "completeness-orphan-manifest-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        orphan_path = Path(event_path + ".replay-commit.orphan.json")
        orphan_path.write_text("not-json", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_completeness_orphan_manifest"):
            executor.audit_replay_evidence_completeness(require_durable_snapshot=True)
        orphan_path.unlink()
        self.assertEqual(executor.audit_replay_evidence_completeness(require_durable_snapshot=True)["manifest_count"], 1)

    def test_startup_completeness_rejects_manifest_path_collision(self):
        event_path = str(Path(self.tmp.name) / "completeness-path-collision-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        self.recovery.begin("run-collision-2", "sha256:before")
        self.recovery.complete("run-collision-2", workspace_after="sha256:after", receipt_id=self.receipt.receipt_id, status="completed")
        proposal = PatchProposal("patch-collision-2", "ws-1", "snap-base", "snap-head", ({"path": "out-collision-2.txt", "kind": "modified"},), "approved")
        self.patches.put(proposal)
        action_two = ExecutionRecoveryAction("action-collision-2", "rollback", "run-collision-2", self.receipt.receipt_id, "patch-collision-2", "ws-1", "snap-base", "operator-1", "session-1")
        executor.handle(action_two, self.context)
        canonical = executor._replay_commit_manifest_path(self.action.action_id)
        with patch.object(executor, "_replay_commit_manifest_path", return_value=canonical):
            with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_completeness_manifest_path_collision"):
                executor.audit_replay_evidence_completeness(require_durable_snapshot=True)
        self.assertEqual(executor.audit_replay_evidence_completeness(require_durable_snapshot=True)["manifest_count"], 2)

    def test_startup_completeness_rejects_orphan_sidecar_filename(self):
        event_path = str(Path(self.tmp.name) / "completeness-orphan-sidecar-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        orphan_path = Path(event_path + ".status.orphan.json")
        orphan_path.write_text("not-json", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_completeness_orphan_sidecar"):
            executor.audit_replay_evidence_completeness(require_durable_snapshot=True)
        orphan_path.unlink()
        self.assertEqual(executor.audit_replay_evidence_completeness(require_durable_snapshot=True)["manifest_count"], 1)

    def test_startup_completeness_rejects_canonical_sidecar_symlink_alias(self):
        event_path = str(Path(self.tmp.name) / "completeness-sidecar-alias-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        status_path = Path(executor._status_snapshot_path(self.action.action_id))
        alias_path = status_path.with_name(status_path.name + ".alias-target")
        status_path.rename(alias_path)
        status_path.symlink_to(alias_path.name)
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_completeness_sidecar_alias"):
            executor.audit_replay_evidence_completeness(require_durable_snapshot=True)
        status_path.unlink()
        alias_path.rename(status_path)
        self.assertEqual(executor.audit_replay_evidence_completeness(require_durable_snapshot=True)["manifest_count"], 1)

    def test_startup_completeness_rejects_external_hardlink_sidecar(self):
        event_path = str(Path(self.tmp.name) / "completeness-hardlink-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        status_path = Path(executor._status_snapshot_path(self.action.action_id))
        original_status = status_path.read_bytes()
        external_target = Path(self.tmp.name).parent / ("external-status-" + self.action.action_id + ".json")
        try:
            external_target.write_bytes(original_status)
            status_path.unlink()
            os.link(external_target, status_path)
            with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_completeness_sidecar_file_identity"):
                executor.audit_replay_evidence_completeness(require_durable_snapshot=True)
        finally:
            if status_path.is_symlink() or status_path.exists():
                status_path.unlink()
            status_path.write_bytes(original_status)
            if external_target.exists():
                external_target.unlink()
        self.assertEqual(executor.audit_replay_evidence_completeness(require_durable_snapshot=True)["manifest_count"], 1)

    def test_startup_completeness_rejects_mixed_sidecar_manifest_generation(self):
        event_path = str(Path(self.tmp.name) / "completeness-mixed-generation-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        status_path = Path(executor._status_snapshot_path(self.action.action_id))
        original_status = status_path.read_bytes()
        mixed_status = json.loads(original_status)
        mixed_status["payload"]["reason"] = "mixed-generation-fixture"
        mixed_status["signature"] = _snapshot_signature(mixed_status["payload"], self.key)
        status_path.write_text(json.dumps(mixed_status, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_completeness_sidecar_digest_mismatch"):
            executor.audit_replay_evidence_completeness(require_durable_snapshot=True)
        status_path.write_bytes(original_status)
        self.assertEqual(executor.audit_replay_evidence_completeness(require_durable_snapshot=True)["manifest_count"], 1)

    def test_generation_receipt_rejects_drift_missing_and_rewrites_deterministically(self):
        event_path = str(Path(self.tmp.name) / "generation-receipt-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        receipt_path = Path(executor._replay_generation_receipt_path())
        original_receipt = receipt_path.read_bytes()
        tampered = json.loads(original_receipt)
        tampered["payload"]["generation_digest"] = "sha256:stale-generation-fixture"
        tampered["signature"] = _snapshot_signature(tampered["payload"], self.key)
        receipt_path.write_text(json.dumps(tampered, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_generation_receipt_drift"):
            executor.audit_replay_evidence_completeness(require_durable_snapshot=True)
        receipt_path.write_bytes(original_receipt)
        self.assertEqual(executor.verify_replay_generation_receipt()["status"], "passed")
        first_bytes = receipt_path.read_bytes()
        executor.persist_replay_generation_receipt()
        self.assertEqual(receipt_path.read_bytes(), first_bytes)
        receipt_path.unlink()
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_generation_receipt_missing"):
            executor.audit_replay_evidence_completeness(require_durable_snapshot=True)
        executor.persist_replay_generation_receipt()
        self.assertEqual(executor.verify_replay_generation_receipt()["status"], "passed")

    def test_generation_receipt_schema_and_process_boundary(self):
        event_path = str(Path(self.tmp.name) / "generation-schema-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        receipt_path = Path(executor._replay_generation_receipt_path())
        original = receipt_path.read_bytes()
        cases = (("unknown", lambda payload: payload.update({"unknown": "fixture"}), "recovery_replay_generation_receipt_unknown_field"), ("missing", lambda payload: payload.pop("files"), "recovery_replay_generation_receipt_missing_field"), ("schema", lambda payload: payload.update({"schema_version": "noesis.recovery-replay-generation-receipt.v0"}), "recovery_replay_generation_receipt_schema_invalid"), ("path", lambda payload: payload.update({"receipt_path": str(Path(self.tmp.name) / "alias.json")}), "recovery_replay_generation_receipt_path_mismatch"))
        for _, mutate, reason in cases:
            tampered = json.loads(original)
            mutate(tampered["payload"])
            tampered["signature"] = _snapshot_signature(tampered["payload"], self.key)
            receipt_path.write_text(json.dumps(tampered, sort_keys=True) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ExecutionRecoveryError, reason):
                executor.verify_replay_generation_receipt()
            receipt_path.write_bytes(original)
        root = Path(__file__).resolve().parents[1]
        child = """import sys
from noesis_harness.execution_assurance import ExecutionReceiptStore, ExecutionRecoveryStore
from noesis_harness.execution_recovery import ExecutionRecoveryExecutor
from noesis_harness.workspaces import PatchReviewStore
root, event_path = sys.argv[1], sys.argv[2]
key = b'execution-recovery-signing-key'
executor = ExecutionRecoveryExecutor(receipt_store=ExecutionReceiptStore(root + '/receipts.db', signing_key=key), recovery_store=ExecutionRecoveryStore(root + '/recovery.db'), patch_store=PatchReviewStore(root + '/patches.db'), event_path=event_path, rollback_handler=lambda _: True)
print(executor.verify_replay_generation_receipt()['status'])
"""
        env = dict(os.environ)
        env["PYTHONPATH"] = str(root)
        process = subprocess.run([sys.executable, "-c", child, str(self.tmp.name), event_path], capture_output=True, text=True, check=True, env=env)
        self.assertEqual(process.stdout.strip(), "passed")
        self.assertEqual(process.stderr, "")

    def test_generation_id_rotates_monotonically_and_rejects_stale_receipt(self):
        event_path = str(Path(self.tmp.name) / "generation-rotation-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        first = executor.verify_replay_generation_receipt()
        self.assertEqual(first["payload"]["generation_id"], 1)
        self.recovery.begin("run-rotation-2", "sha256:before")
        self.recovery.complete("run-rotation-2", workspace_after="sha256:after", receipt_id=self.receipt.receipt_id, status="completed")
        proposal = PatchProposal("patch-rotation-2", "ws-1", "snap-base", "snap-head", (("path", "out-rotation-2.txt"),), "approved")
        self.patches.put(proposal)
        action_two = ExecutionRecoveryAction("action-rotation-2", "rollback", "run-rotation-2", self.receipt.receipt_id, "patch-rotation-2", "ws-1", "snap-base", "operator-1", "session-1")
        executor.handle(action_two, self.context)
        second = executor.verify_replay_generation_receipt()
        self.assertEqual(second["payload"]["generation_id"], 2)
        self.assertNotEqual(first["payload"]["generation_digest"], second["payload"]["generation_digest"])
        self.assertNotEqual(first["payload"]["event_chain_digest"], second["payload"]["event_chain_digest"])
        self.assertNotEqual(first["payload"]["completeness_digest"], second["payload"]["completeness_digest"])
        receipt_path = Path(executor._replay_generation_receipt_path())
        stale = json.loads(receipt_path.read_bytes())
        stale["payload"]["generation_id"] = 1
        stale["payload"]["generation_digest"] = first["payload"]["generation_digest"]
        stale["signature"] = _snapshot_signature(stale["payload"], self.key)
        receipt_path.write_text(json.dumps(stale, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_generation_receipt_stale"):
            executor.verify_replay_generation_receipt()
        receipt_path.write_bytes(json.dumps(second, sort_keys=True).encode("utf-8") + b"\n")
        cross_bound = json.loads(receipt_path.read_bytes())
        cross_bound["payload"]["event_chain_digest"] = first["payload"]["event_chain_digest"]
        cross_bound["payload"]["completeness_digest"] = first["payload"]["completeness_digest"]
        cross_bound["signature"] = _snapshot_signature(cross_bound["payload"], self.key)
        receipt_path.write_text(json.dumps(cross_bound, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_generation_receipt_drift"):
            executor.verify_replay_generation_receipt()

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

    def test_replay_completeness_rejects_catalog_snapshot_drift(self):
        event_path = str(Path(self.tmp.name) / "catalog-drift-completeness-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        snapshot_path = Path(executor._replay_catalog_snapshot_path())
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot["payload"]["records"][0]["action_digest"] = "sha256:tampered"
        snapshot["signature"] = _snapshot_signature(snapshot["payload"], self.key)
        snapshot_path.write_text(json.dumps(snapshot, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_catalog_snapshot_drift"):
            executor.audit_replay_evidence_completeness()

    def test_replay_completeness_rejects_sidecar_digest_mismatch(self):
        event_path = str(Path(self.tmp.name) / "sidecar-digest-completeness-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        snapshot_path = Path(executor._replay_snapshot_path(self.action.action_id))
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot["payload"]["action_digest"] = "sha256:tampered"
        snapshot["signature"] = _snapshot_signature(snapshot["payload"], self.key)
        snapshot_path.write_text(json.dumps(snapshot, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ExecutionRecoveryError, "recovery_replay_completeness_sidecar_digest_mismatch"):
            executor.audit_replay_evidence_completeness()

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

    def test_replay_commit_manifest_rejects_event_chain_digest_substitution(self):
        event_path = str(Path(self.tmp.name) / "commit-manifest-chain-root-events.jsonl")
        executor = ExecutionRecoveryExecutor(receipt_store=self.receipts, recovery_store=self.recovery, patch_store=self.patches, event_path=event_path, rollback_handler=lambda _: True)
        executor.handle(self.action, self.context)
        snapshot_path = Path(executor._replay_commit_manifest_path(self.action.action_id))
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot["payload"]["replay_event_chain_digest"] = "sha256:old-prefix"
        snapshot["payload"]["bundle_digest"] = executor._replay_bundle_digest(snapshot["payload"])
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

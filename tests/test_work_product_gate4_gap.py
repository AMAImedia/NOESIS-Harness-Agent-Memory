import json
import tempfile
import unittest
from pathlib import Path

from noesis_harness.event_store import EventStore
from noesis_harness.multi_agent_runtime import MultiAgentCoordinator
from noesis_harness.multi_agent_workflow import MultiAgentWorkProductLoop
from noesis_harness.task_session_api import TaskSessionStore
from noesis_harness.work_product_benchmark import (
    COMMIT_MARKER_SCHEMA,
    MARKER_STATUS_COMMITTED,
    MARKER_STATUS_REPLAYED,
    WorkProductBenchmarkError,
    WorkProductCommitMarker,
    WorkProductCommitMarkerLedger,
)
from noesis_harness.workspaces import MergeAuthorization, WorkspaceManager


def _marker(**overrides):
    values = {
        "product_id": "product:a1b2c3d4",
        "task_id": "task-1",
        "agent_id": "coder",
        "workspace_id": "sess-1--coder--000111222333",
        "base_snapshot_id": "snap_base",
        "head_snapshot_id": "snap_head",
        "artifact_digest": "sha256:" + "0" * 64,
        "authorization_digest": "sha256:" + "1" * 64,
    }
    values.update(overrides)
    return WorkProductCommitMarker(**values)


class CommitMarkerLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / "commit-markers.jsonl")

    def tearDown(self):
        self.tmp.cleanup()

    def _line_count(self):
        with open(self.path, "rb") as handle:
            return len([line for line in handle.read().splitlines() if line.strip()])

    def test_double_send_is_absorbed_as_replay(self):
        ledger = WorkProductCommitMarkerLedger(self.path)
        marker = _marker()
        first = ledger.record(marker)
        second = ledger.record(marker)
        self.assertEqual(first.status, MARKER_STATUS_COMMITTED)
        self.assertFalse(first.duplicate)
        self.assertEqual(second.status, MARKER_STATUS_REPLAYED)
        self.assertTrue(second.duplicate)
        self.assertEqual(first.marker_id, second.marker_id)
        self.assertEqual(ledger.count(), 1)
        self.assertEqual(self._line_count(), 1)

    def test_conflicting_resubmission_for_same_product_fails_closed(self):
        ledger = WorkProductCommitMarkerLedger(self.path)
        marker = _marker()
        ledger.record(marker)
        forged = _marker(authorization_digest="sha256:" + "9" * 64)
        with self.assertRaisesRegex(WorkProductBenchmarkError, "commit_marker_conflict"):
            ledger.record(forged)
        self.assertEqual(ledger.count(), 1)
        stored = ledger.get(marker.product_id)
        self.assertIsNotNone(stored)
        self.assertEqual(stored.marker_id, marker.marker_id)

    def test_restart_replays_identical_projection_and_absorbs_double_send(self):
        first = WorkProductCommitMarkerLedger(self.path)
        marker = _marker()
        first.record(marker)
        second = WorkProductCommitMarkerLedger(self.path)
        self.assertEqual(second.markers(), first.markers())
        self.assertEqual(second.count(), 1)
        replay = second.record(marker)
        self.assertEqual(replay.status, MARKER_STATUS_REPLAYED)
        self.assertEqual(self._line_count(), 1)

    def test_torn_tail_from_crash_is_repaired_on_reopen(self):
        ledger = WorkProductCommitMarkerLedger(self.path)
        ledger.record(_marker(product_id="product:one"))
        ledger.record(_marker(product_id="product:two"))
        with open(self.path, "ab") as handle:
            handle.write(b'{"event_id": "marker:crash')
        reopened = WorkProductCommitMarkerLedger(self.path)
        self.assertEqual(reopened.count(), 2)
        third = reopened.record(_marker(product_id="product:three"))
        self.assertEqual(third.status, MARKER_STATUS_COMMITTED)
        self.assertEqual(reopened.count(), 3)
        report = reopened.verify_integrity()
        self.assertTrue(report["ok"])
        self.assertEqual(report["markers"], 3)

    def test_midfile_tampering_fails_closed(self):
        ledger = WorkProductCommitMarkerLedger(self.path)
        ledger.record(_marker())
        with open(self.path, "r", encoding="utf-8") as handle:
            lines = [json.loads(line) for line in handle if line.strip()]
        lines[0]["payload"]["artifact_digest"] = "sha256:" + "f" * 64
        with open(self.path, "w", encoding="utf-8") as handle:
            for record in lines:
                handle.write(json.dumps(record) + "\n")
        with self.assertRaisesRegex(WorkProductBenchmarkError, "commit_marker_tampered"):
            WorkProductCommitMarkerLedger(self.path)

    def test_unexpected_event_type_fails_closed(self):
        EventStore(self.path).append("unrelated_event", {"product_id": "product:x"})
        with self.assertRaisesRegex(WorkProductBenchmarkError, "ledger_unexpected_event"):
            WorkProductCommitMarkerLedger(self.path)

    def test_malformed_or_foreign_payloads_fail_closed(self):
        with self.assertRaisesRegex(WorkProductBenchmarkError, "commit_marker_payload_invalid"):
            WorkProductCommitMarker.from_mapping({})
        extra = dict(_marker().to_mapping())
        extra["extra_key"] = "no"
        with self.assertRaisesRegex(WorkProductBenchmarkError, "commit_marker_payload_invalid"):
            WorkProductCommitMarker.from_mapping(extra)
        with self.assertRaisesRegex(WorkProductBenchmarkError, "unsupported_commit_marker_schema"):
            _marker(schema_version="noesis.other.v9")
        with self.assertRaisesRegex(WorkProductBenchmarkError, "task_id_required"):
            _marker(task_id="")
        with self.assertRaisesRegex(WorkProductBenchmarkError, "commit_marker_type_required"):
            WorkProductCommitMarkerLedger(self.path).record({"product_id": "not-a-marker"})

    def test_verify_integrity_reports_durable_state(self):
        ledger = WorkProductCommitMarkerLedger(self.path)
        ledger.record(_marker(product_id="product:one"))
        ledger.record(_marker(product_id="product:two"))
        report = ledger.verify_integrity()
        self.assertTrue(report["ok"])
        self.assertEqual(report["markers"], 2)
        self.assertEqual(report["records"], 2)
        self.assertEqual(report["schema_version"], COMMIT_MARKER_SCHEMA)


class WorkflowGate4GapTests(unittest.TestCase):
    """Coverage locks for previously untested loop-level Gate 4 behaviors."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.tasks = TaskSessionStore(str(root / "tasks.jsonl"))
        self.tasks.create_session("lead", session_id="sess-1")
        self.tasks.create_task("sess-1", "Implement patch", "lead", task_id="task-1")
        self.workspaces = WorkspaceManager(str(root / "workspaces"))
        self.coordinator = MultiAgentCoordinator(self.tasks, self.workspaces, str(root / "coordination.jsonl"))
        self.coordinator.register_agent("coder", "coder", ("workspace.write",))
        self.coordinator.register_agent("reviewer", "reviewer", ("workspace.read",))
        self.loop = MultiAgentWorkProductLoop(self.coordinator, str(root / "products.jsonl"))

    def tearDown(self):
        self.tmp.cleanup()

    def _submitted_product(self):
        claim = self.coordinator.claim("sess-1", "task-1", "coder")
        self.workspaces.write_text(claim.workspace_id, "result.txt", "safe patch\n")
        base = self.workspaces.snapshot(claim.workspace_id)
        self.workspaces.write_text(claim.workspace_id, "result.txt", "reviewed patch\n")
        head = self.workspaces.snapshot(claim.workspace_id, parent_snapshot_id=base.snapshot_id)
        product = self.loop.submit(task_id="task-1", agent_id="coder", base_snapshot_id=base.snapshot_id, head_snapshot_id=head.snapshot_id, summary="ready")
        return claim, base, head, product

    @staticmethod
    def _authorization(review, claim, base, head):
        return MergeAuthorization(review["proposal_id"], claim.workspace_id, base.snapshot_id, head.snapshot_id, "reviewer", review.get("authorization_digest", ""))

    def _committed_state(self):
        claim, base, head, product = self._submitted_product()
        review = self.loop.review(product, reviewer_id="reviewer", decision="approved", current_base_snapshot_id=base.snapshot_id)
        authorization = self._authorization(review, claim, base, head)
        committed = self.loop.commit(product, authorization=authorization)
        return claim, base, head, product, review, committed

    def test_submit_double_send_is_idempotent_single_event(self):
        claim, base, head, product = self._submitted_product()
        duplicate = self.loop.submit(task_id="task-1", agent_id="coder", base_snapshot_id=base.snapshot_id, head_snapshot_id=head.snapshot_id, summary="ready")
        self.assertEqual(duplicate["product_id"], product.product_id)
        submitted = [event for event in self.loop.events.iter_events() if event["type"] == "work_product_submitted"]
        self.assertEqual(len(submitted), 1)
        self.assertEqual(self.tasks.task("task-1").state, "review")

    def test_commit_double_send_returns_replayed_once(self):
        claim, base, head, product, review, first = self._committed_state()
        self.assertEqual(first["status"], "committed")
        replayed = self.loop.commit(product, authorization=self._authorization(review, claim, base, head))
        self.assertEqual(replayed["status"], "replayed")
        commits = [event for event in self.loop.events.iter_events() if event["type"] == "work_product_committed"]
        self.assertEqual(len(commits), 1)
        self.assertEqual(commits[0]["payload"]["files_applied"], False)
        self.assertEqual(self.tasks.task("task-1").state, "committed")

    def test_commit_marker_survives_restart_as_replay(self):
        claim, base, head, product, review, _ = self._committed_state()
        authorization = self._authorization(review, claim, base, head)
        before = self.loop.resume("sess-1")
        reopened = MultiAgentWorkProductLoop(self.coordinator, str(Path(self.tmp.name) / "products.jsonl"))
        after = reopened.resume("sess-1")
        self.assertEqual(before["event_count"], after["event_count"])
        replayed = reopened.commit(product, authorization=authorization)
        self.assertEqual(replayed["status"], "replayed")
        commits = [event for event in reopened.events.iter_events() if event["type"] == "work_product_committed"]
        self.assertEqual(len(commits), 1)

    def test_reviewer_rejection_blocks_commit_fail_closed(self):
        claim, base, head, product = self._submitted_product()
        rejected = self.loop.review(product, reviewer_id="reviewer", decision="rejected", current_base_snapshot_id=base.snapshot_id)
        self.assertFalse(rejected["merge_authorized"])
        authorization = self._authorization(rejected, claim, base, head)
        with self.assertRaisesRegex(Exception, "merge_authorization_required"):
            self.loop.commit(product, authorization=authorization)
        self.assertEqual(self.tasks.task("task-1").state, "review")
        commits = [event for event in self.loop.events.iter_events() if event["type"] == "work_product_committed"]
        self.assertEqual(commits, [])

    def test_commit_without_review_fails_closed(self):
        claim, base, head, product = self._submitted_product()
        forged = MergeAuthorization("patch_forged", claim.workspace_id, base.snapshot_id, head.snapshot_id, "reviewer", "sha256:forged")
        with self.assertRaisesRegex(Exception, "merge_authorization_required"):
            self.loop.commit(product, authorization=forged)
        self.assertEqual(self.tasks.task("task-1").state, "review")

    def test_loop_commit_binds_to_durable_commit_ledger(self):
        claim, base, head, product, review, _ = self._committed_state()
        path = str(Path(self.tmp.name) / "markers.jsonl")
        ledger = WorkProductCommitMarkerLedger(path)
        marker = WorkProductCommitMarker(
            product_id=product.product_id,
            task_id=product.task_id,
            agent_id=product.agent_id,
            workspace_id=claim.workspace_id,
            base_snapshot_id=product.base_snapshot_id,
            head_snapshot_id=product.head_snapshot_id,
            artifact_digest=product.artifact_digest,
            authorization_digest=review["authorization_digest"],
        )
        first = ledger.record(marker)
        second = ledger.record(marker)
        self.assertEqual(first.status, MARKER_STATUS_COMMITTED)
        self.assertEqual(second.status, MARKER_STATUS_REPLAYED)
        reopened = WorkProductCommitMarkerLedger(path)
        self.assertIsNotNone(reopened.get(product.product_id))
        self.assertEqual(reopened.verify_integrity()["markers"], 1)


if __name__ == "__main__":
    unittest.main()

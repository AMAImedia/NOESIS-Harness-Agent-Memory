import tempfile
import unittest
from pathlib import Path

from noesis_harness.multi_agent_runtime import MultiAgentCoordinator
from noesis_harness.multi_agent_workflow import MultiAgentWorkProductLoop, WorkProductError
from noesis_harness.task_session_api import TaskSessionStore
from noesis_harness.work_product_benchmark import COMMIT_MARKER_SCHEMA, WorkProductCommitMarker, WorkProductCommitMarkerLedger
from noesis_harness.workspaces import MergeAuthorization, WorkspaceManager


class MultiAgentWorkflowMarkerTests(unittest.TestCase):
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
        self.ledger = WorkProductCommitMarkerLedger(str(root / "markers.jsonl"))
        self.loop = MultiAgentWorkProductLoop(self.coordinator, str(root / "products.jsonl"), marker_ledger=self.ledger)

    def tearDown(self):
        self.tmp.cleanup()

    def _product(self, loop):
        claim = self.coordinator.claim("sess-1", "task-1", "coder")
        self.workspaces.write_text(claim.workspace_id, "result.txt", "safe patch\n")
        base = self.workspaces.snapshot(claim.workspace_id)
        self.workspaces.write_text(claim.workspace_id, "result.txt", "reviewed patch\n")
        head = self.workspaces.snapshot(claim.workspace_id, parent_snapshot_id=base.snapshot_id)
        product = loop.submit(task_id="task-1", agent_id="coder", base_snapshot_id=base.snapshot_id, head_snapshot_id=head.snapshot_id, summary="ready")
        return claim, base, head, product

    def _approved(self, loop, claim, base, head, product):
        review = loop.review(product, reviewer_id="reviewer", decision="approved", current_base_snapshot_id=base.snapshot_id)
        self.assertTrue(review["merge_authorized"])
        return MergeAuthorization(review["proposal_id"], claim.workspace_id, base.snapshot_id, head.snapshot_id, "reviewer", review["authorization_digest"])

    def test_successful_commit_records_exactly_one_marker(self):
        claim, base, head, product = self._product(self.loop)
        authorization = self._approved(self.loop, claim, base, head, product)
        committed = self.loop.commit(product, authorization=authorization)
        self.assertEqual(committed["status"], "committed")
        markers = self.ledger.markers()
        self.assertEqual(len(markers), 1)
        marker = markers[0]
        self.assertEqual(marker.product_id, product.product_id)
        self.assertEqual(marker.task_id, "task-1")
        self.assertEqual(marker.agent_id, "coder")
        self.assertEqual(marker.workspace_id, claim.workspace_id)
        self.assertEqual(marker.base_snapshot_id, base.snapshot_id)
        self.assertEqual(marker.head_snapshot_id, head.snapshot_id)
        self.assertEqual(marker.artifact_digest, product.artifact_digest)
        self.assertEqual(marker.authorization_digest, authorization.authorization_digest)
        self.assertEqual(marker.schema_version, COMMIT_MARKER_SCHEMA)
        self.assertTrue(self.ledger.verify_integrity()["ok"])

    def test_double_commit_is_replayed_not_duplicated(self):
        claim, base, head, product = self._product(self.loop)
        authorization = self._approved(self.loop, claim, base, head, product)
        first = self.loop.commit(product, authorization=authorization)
        self.assertEqual(first["status"], "committed")
        second = self.loop.commit(product, authorization=authorization)
        self.assertEqual(second["status"], "replayed")
        self.assertEqual(len(self.ledger.markers()), 1)
        duplicate = self.ledger.record(WorkProductCommitMarker(product.product_id, product.task_id, product.agent_id, product.workspace_id, product.base_snapshot_id, product.head_snapshot_id, product.artifact_digest, authorization.authorization_digest))
        self.assertEqual(duplicate.status, "replayed")
        self.assertTrue(duplicate.duplicate)
        self.assertEqual(len(self.ledger.markers()), 1)

    def test_conflicting_marker_fails_closed(self):
        claim, base, head, product = self._product(self.loop)
        authorization = self._approved(self.loop, claim, base, head, product)
        forged = WorkProductCommitMarker(product.product_id, product.task_id, product.agent_id, product.workspace_id, product.base_snapshot_id, product.head_snapshot_id, product.artifact_digest, "sha256:forged-authorization")
        record = self.ledger.record(forged)
        self.assertEqual(record.status, "committed")
        with self.assertRaisesRegex(WorkProductError, "commit_marker_conflict"):
            self.loop.commit(product, authorization=authorization)
        self.assertEqual(self.tasks.task("task-1").state, "review")
        events = [event for event in self.loop.events.iter_events() if event.get("type") == "work_product_committed"]
        self.assertEqual(events, [])

    def test_resume_exposes_marker_projection(self):
        claim, base, head, product = self._product(self.loop)
        authorization = self._approved(self.loop, claim, base, head, product)
        self.loop.commit(product, authorization=authorization)
        resumed = self.loop.resume("sess-1")
        projection = resumed["commit_markers"]
        self.assertEqual(projection["count"], 1)
        self.assertEqual(projection["last_marker_id"], self.ledger.get(product.product_id).marker_id)
        self.assertTrue(str(projection["last_marker_id"]).startswith("marker:"))
        reopened = MultiAgentWorkProductLoop(self.coordinator, str(Path(self.tmp.name) / "products.jsonl"), marker_ledger=self.ledger)
        replayed_view = reopened.resume("sess-1")
        self.assertEqual(replayed_view["commit_markers"], resumed["commit_markers"])

    def test_none_ledger_keeps_old_behavior(self):
        root = Path(self.tmp.name)
        plain = MultiAgentWorkProductLoop(self.coordinator, str(root / "products_plain.jsonl"))
        self.assertIsNone(plain.marker_ledger)
        claim, base, head, product = self._product(plain)
        authorization = self._approved(plain, claim, base, head, product)
        committed = plain.commit(product, authorization=authorization)
        self.assertEqual(committed["status"], "committed")
        self.assertFalse(committed["files_applied"])
        self.assertEqual(self.tasks.task("task-1").state, "committed")
        resumed = plain.resume("sess-1")
        self.assertNotIn("commit_markers", resumed)
        self.assertEqual(resumed["tasks"][0].task_id, "task-1")
        self.assertEqual(len(self.ledger.markers()), 0)


if __name__ == "__main__":
    unittest.main()

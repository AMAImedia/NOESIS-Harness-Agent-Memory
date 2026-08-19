import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from noesis_harness.multi_agent_runtime import MultiAgentCoordinator, MultiAgentError
from noesis_harness.multi_agent_workflow import MultiAgentWorkProductLoop, WorkProductError
from noesis_harness.task_session_api import TaskSessionStore
from noesis_harness.workspaces import WorkspaceManager


class MultiAgentWorkProductTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.tasks = TaskSessionStore(str(root / "tasks.jsonl"))
        self.tasks.create_session("lead", session_id="sess-1")
        self.task = self.tasks.create_task("sess-1", "Implement patch", "lead", task_id="task-1")
        self.workspaces = WorkspaceManager(str(root / "workspaces"))
        self.coordinator = MultiAgentCoordinator(self.tasks, self.workspaces, str(root / "coordination.jsonl"))
        self.coordinator.register_agent("coder", "coder", ("workspace.write",))
        self.coordinator.register_agent("reviewer", "reviewer", ("workspace.read",))
        self.loop = MultiAgentWorkProductLoop(self.coordinator, str(root / "products.jsonl"))

    def tearDown(self):
        self.tmp.cleanup()

    def _product(self):
        claim = self.coordinator.claim("sess-1", "task-1", "coder")
        self.workspaces.write_text(claim.workspace_id, "result.txt", "safe patch\n")
        base = self.workspaces.snapshot(claim.workspace_id)
        self.workspaces.write_text(claim.workspace_id, "result.txt", "reviewed patch\n")
        head = self.workspaces.snapshot(claim.workspace_id, parent_snapshot_id=base.snapshot_id)
        product = self.loop.submit(task_id="task-1", agent_id="coder", base_snapshot_id=base.snapshot_id, head_snapshot_id=head.snapshot_id, summary="ready")
        return claim, base, head, product

    def test_governed_execution_binds_receipt_to_claimed_workspace_before_review(self):
        claim = self.coordinator.claim("sess-1", "task-1", "coder")
        base = self.workspaces.snapshot(claim.workspace_id)
        request = SimpleNamespace(workspace=str(self.workspaces.path(claim.workspace_id)), request_id="exec-1")

        class Runtime:
            def __init__(self):
                self.receipt_store = SimpleNamespace(get=lambda receipt_id: SimpleNamespace(receipt_id=receipt_id, outcome="committed"))

            def run(self, value):
                self.path = Path(value.workspace) / "result.txt"
                self.path.write_text("runtime product\n", encoding="utf-8")
                return SimpleNamespace(status="completed", request_id=value.request_id, sandboxed=True, receipt=SimpleNamespace(outcome="committed", receipt_id="receipt-exec-1"))

        RuntimeInstance = Runtime()
        head = self.workspaces.snapshot(claim.workspace_id, parent_snapshot_id=base.snapshot_id)
        product = self.loop.execute_and_submit(runtime=RuntimeInstance, request=request, task_id="task-1", agent_id="coder", base_snapshot_id=base.snapshot_id, head_snapshot_id=head.snapshot_id, summary="runtime product")
        self.assertEqual(product.agent_id, "coder")
        submitted = [event["payload"] for event in self.loop.events.iter_events() if event["type"] == "work_product_submitted"][-1]
        self.assertEqual(submitted["execution"]["receipt_id"], "receipt-exec-1")
        self.assertTrue(submitted["execution"]["sandboxed"])

    def test_governed_execution_rejects_wrong_workspace_and_failed_result(self):
        claim = self.coordinator.claim("sess-1", "task-1", "coder")
        base = self.workspaces.snapshot(claim.workspace_id)
        head = self.workspaces.snapshot(claim.workspace_id, parent_snapshot_id=base.snapshot_id)
        wrong = SimpleNamespace(workspace=str(Path(self.tmp.name)), request_id="exec-wrong")
        with self.assertRaisesRegex(WorkProductError, "execution_workspace_mismatch"):
            self.loop.execute_and_submit(runtime=SimpleNamespace(run=lambda _: None), request=wrong, task_id="task-1", agent_id="coder", base_snapshot_id=base.snapshot_id, head_snapshot_id=head.snapshot_id)
        request = SimpleNamespace(workspace=str(self.workspaces.path(claim.workspace_id)), request_id="exec-failed")
        failed = SimpleNamespace(receipt_store=SimpleNamespace(get=lambda _: None), run=lambda _: SimpleNamespace(status="failed", request_id="exec-failed", receipt=None))
        with self.assertRaisesRegex(WorkProductError, "delegated_execution_not_completed"):
            self.loop.execute_and_submit(runtime=failed, request=request, task_id="task-1", agent_id="coder", base_snapshot_id=base.snapshot_id, head_snapshot_id=head.snapshot_id)

    def test_delegated_product_requires_independent_review_and_explicit_commit(self):
        claim, base, head, product = self._product()
        with self.assertRaisesRegex(WorkProductError, "independent_reviewer_required"):
            self.loop.review(product, reviewer_id="coder", decision="approved", current_base_snapshot_id=base.snapshot_id)
        review = self.loop.review(product, reviewer_id="reviewer", decision="approved", current_base_snapshot_id=base.snapshot_id)
        self.assertTrue(review["merge_authorized"])
        from noesis_harness.workspaces import MergeAuthorization
        authorization = MergeAuthorization(review["proposal_id"], claim.workspace_id, base.snapshot_id, head.snapshot_id, "reviewer", review["authorization_digest"])
        committed = self.loop.commit(product, authorization=authorization)
        self.assertEqual(committed["status"], "committed")
        self.assertFalse(committed["files_applied"])
        self.assertEqual(self.tasks.task("task-1").state, "committed")

    def test_stale_base_and_duplicate_review_fail_closed(self):
        claim, base, head, product = self._product()
        with self.assertRaisesRegex(WorkProductError, "merge_base_stale"):
            self.loop.review(product, reviewer_id="reviewer", decision="approved", current_base_snapshot_id=head.snapshot_id)
        review = self.loop.review(product, reviewer_id="reviewer", decision="rejected", current_base_snapshot_id=base.snapshot_id)
        self.assertFalse(review["merge_authorized"])
        replay = self.loop.review(product, reviewer_id="reviewer", decision="rejected", current_base_snapshot_id=base.snapshot_id)
        self.assertEqual(replay["status"], "replayed")
        with self.assertRaisesRegex(WorkProductError, "work_product_review_conflict"):
            self.loop.review(product, reviewer_id="reviewer", decision="approved", current_base_snapshot_id=base.snapshot_id)

    def test_cross_agent_submission_and_resume_are_denied_or_durable(self):
        claim = self.coordinator.claim("sess-1", "task-1", "coder")
        base = self.workspaces.snapshot(claim.workspace_id)
        with self.assertRaisesRegex(WorkProductError, "claim_owner_required"):
            self.loop.submit(task_id="task-1", agent_id="reviewer", base_snapshot_id=base.snapshot_id, head_snapshot_id=base.snapshot_id)
        resumed = self.loop.resume("sess-1")
        self.assertEqual(resumed["tasks"][0].task_id, "task-1")
        self.assertEqual(resumed["claims"][0].agent_id, "coder")
        reopened = MultiAgentWorkProductLoop(self.coordinator, str(Path(self.tmp.name) / "products.jsonl"))
        self.assertEqual(reopened.resume("sess-1")["event_count"], resumed["event_count"])


if __name__ == "__main__":
    unittest.main()

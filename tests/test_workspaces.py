import tempfile
import unittest
from pathlib import Path

from noesis_harness.workspaces import PatchReviewStore, WorkspaceError, WorkspaceManager


class WorkspaceManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.manager = WorkspaceManager(self.tmp.name)
        self.workspace = self.manager.create("session-1", "agent-a")

    def tearDown(self):
        self.tmp.cleanup()

    def test_safe_write_and_snapshot_diff(self):
        self.manager.write_text(self.workspace, "src/main.py", "print('one')\n")
        base = self.manager.snapshot(self.workspace)
        self.manager.write_text(self.workspace, "src/main.py", "print('two')\n")
        self.manager.write_text(self.workspace, "README.md", "draft\n")
        head = self.manager.snapshot(self.workspace, parent_snapshot_id=base.snapshot_id)
        proposal = self.manager.propose_patch(base.snapshot_id, head.snapshot_id)
        self.assertEqual(proposal.status, "needs_review")
        self.assertEqual([change["kind"] for change in proposal.changes], ["added", "modified"])
        self.assertEqual(self.manager.review(proposal, "approved").status, "approved")

    def test_patch_review_store_reopens_and_rejects_conflicting_mutation(self):
        review_store = PatchReviewStore(str(Path(self.tmp.name) / "patch-reviews.db"))
        manager = WorkspaceManager(str(Path(self.tmp.name) / "durable-workspaces"), review_store=review_store)
        workspace = manager.create("session-2", "agent-b")
        base = manager.snapshot(workspace)
        manager.write_text(workspace, "change.txt", "draft\n")
        head = manager.snapshot(workspace, parent_snapshot_id=base.snapshot_id)
        proposal = manager.propose_patch(base.snapshot_id, head.snapshot_id)
        approved = manager.review(proposal, "approved")
        reopened = PatchReviewStore(str(Path(self.tmp.name) / "patch-reviews.db"))
        self.assertEqual(reopened.get(proposal.proposal_id).status, "approved")
        with self.assertRaisesRegex(WorkspaceError, "patch_review_conflict"):
            reopened.put(type(approved)(approved.proposal_id, approved.workspace_id, approved.base_snapshot_id, approved.head_snapshot_id, approved.changes, "rejected"))

    def test_deleted_file_is_reported(self):
        self.manager.write_text(self.workspace, "old.txt", "old\n")
        base = self.manager.snapshot(self.workspace)
        (Path(self.tmp.name) / self.workspace / "old.txt").unlink()
        head = self.manager.snapshot(self.workspace, parent_snapshot_id=base.snapshot_id)
        proposal = self.manager.propose_patch(base.snapshot_id, head.snapshot_id)
        self.assertEqual(proposal.changes[0]["kind"], "deleted")

    def test_path_escape_and_marker_are_denied(self):
        with self.assertRaises(WorkspaceError):
            self.manager.write_text(self.workspace, "../escape.txt", "no")
        with self.assertRaises(WorkspaceError):
            self.manager.write_text(self.workspace, ".noesis-workspace", "overwrite")
        with self.assertRaises(WorkspaceError):
            self.manager.write_text(self.workspace, "/absolute.txt", "no")

    def test_cross_workspace_diff_is_denied(self):
        other = self.manager.create("session-1", "agent-b")
        left = self.manager.snapshot(self.workspace)
        right = self.manager.snapshot(other)
        with self.assertRaises(WorkspaceError):
            self.manager.propose_patch(left.snapshot_id, right.snapshot_id)

    def test_merge_authorization_requires_review_independent_reviewer_and_fresh_base(self):
        self.manager.write_text(self.workspace, "README.md", "draft\n")
        base = self.manager.snapshot(self.workspace)
        self.manager.write_text(self.workspace, "README.md", "approved\n")
        head = self.manager.snapshot(self.workspace, parent_snapshot_id=base.snapshot_id)
        proposal = self.manager.review(self.manager.propose_patch(base.snapshot_id, head.snapshot_id), "approved")
        receipt = self.manager.authorize_merge(proposal, reviewer="reviewer-1", current_base_snapshot_id=base.snapshot_id)
        self.assertEqual(receipt.reviewer, "reviewer-1")
        self.assertTrue(receipt.authorization_digest.startswith("sha256:"))
        with self.assertRaisesRegex(WorkspaceError, "merge_base_stale"):
            self.manager.authorize_merge(proposal, reviewer="reviewer-1", current_base_snapshot_id=head.snapshot_id)

    def test_merge_authorization_does_not_apply_changes(self):
        self.manager.write_text(self.workspace, "README.md", "draft\n")
        base = self.manager.snapshot(self.workspace)
        self.manager.write_text(self.workspace, "README.md", "new\n")
        head = self.manager.snapshot(self.workspace, parent_snapshot_id=base.snapshot_id)
        proposal = self.manager.review(self.manager.propose_patch(base.snapshot_id, head.snapshot_id), "approved")
        before = Path(self.tmp.name, self.workspace, "README.md").read_text()
        self.manager.authorize_merge(proposal, reviewer="reviewer-1", current_base_snapshot_id=base.snapshot_id)
        self.assertEqual(Path(self.tmp.name, self.workspace, "README.md").read_text(), before)


if __name__ == "__main__":
    unittest.main()

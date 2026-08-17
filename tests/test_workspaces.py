import tempfile
import unittest
from pathlib import Path

from noesis_harness.workspaces import WorkspaceError, WorkspaceManager


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


if __name__ == "__main__":
    unittest.main()

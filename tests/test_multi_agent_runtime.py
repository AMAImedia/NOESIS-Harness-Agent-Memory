import tempfile
import unittest
from pathlib import Path

from noesis_harness.multi_agent_runtime import MultiAgentCoordinator, MultiAgentError
from noesis_harness.task_session_api import TaskSessionStore
from noesis_harness.workspaces import WorkspaceManager


class MultiAgentRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.tasks = TaskSessionStore(str(root / "tasks.jsonl"))
        self.tasks.create_session("lead", session_id="sess-1")
        self.task = self.tasks.create_task("sess-1", "Inspect patch", "lead", task_id="task-1")
        self.workspaces = WorkspaceManager(str(root / "workspaces"))
        self.coordinator = MultiAgentCoordinator(self.tasks, self.workspaces, str(root / "agents.jsonl"))
        self.coordinator.register_agent("agent-a", "coder", ("workspace.write",))
        self.coordinator.register_agent("agent-b", "reviewer", ("workspace.read",))

    def tearDown(self):
        self.tmp.cleanup()

    def test_exclusive_claim_and_review(self):
        claim = self.coordinator.claim("sess-1", "task-1", "agent-a")
        self.assertTrue(claim.workspace_id.startswith("sess-1--agent-a--"))
        with self.assertRaises(MultiAgentError):
            self.coordinator.claim("sess-1", "task-1", "agent-b")
        review = self.coordinator.complete_for_review("task-1", "agent-a", "patch ready")
        self.assertEqual(review["status"], "review")

    def test_handoff_preserves_workspace_and_changes_owner(self):
        claim = self.coordinator.claim("sess-1", "task-1", "agent-a")
        handoff = self.coordinator.handoff("task-1", "agent-a", "agent-b", "please review")
        self.assertEqual(handoff["workspace_id"], claim.workspace_id)
        with self.assertRaises(MultiAgentError):
            self.coordinator.complete_for_review("task-1", "agent-a")
        self.assertEqual(self.coordinator.complete_for_review("task-1", "agent-b")["agent_id"], "agent-b")

    def test_resume_returns_durable_coordination_view(self):
        self.coordinator.claim("sess-1", "task-1", "agent-a")
        resumed = self.coordinator.resume("sess-1")
        self.assertEqual(resumed["schema_version"], "noesis.multi-agent.v1")
        self.assertEqual(resumed["tasks"][0].task_id, "task-1")
        self.assertEqual(resumed["claims"][0].agent_id, "agent-a")


if __name__ == "__main__":
    unittest.main()

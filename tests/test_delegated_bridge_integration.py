import tempfile
import unittest
from pathlib import Path

from noesis_harness.coordination import Actions
from noesis_harness.delegated_resume import DelegatedResumeStore
from noesis_harness.execution_bridge import TaskExecutionBridge, TaskExecutionBridgeError, TaskExecutionRequest
from noesis_harness.health_server import HealthServer
from noesis_harness.parallel_agent import SafeParallelExecutor
from noesis_harness.task_session_api import TaskSessionStore


class DelegatedBridgeIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.sessions = TaskSessionStore(str(root / "sessions.jsonl"))
        self.actions = Actions(str(root / "actions.db"))
        self.executor = SafeParallelExecutor(str(root / "workspaces"), max_concurrency=1)
        self.resume = DelegatedResumeStore(str(root / "delegations.jsonl"))
        self.session = self.sessions.create_session("operator", session_id="s-resume")
        self.sessions.create_task("s-resume", "delegated", "agent", task_id="task-resume")
        self.sessions.transition_task("task-resume", "planned")
        self.sessions.transition_task("task-resume", "waiting_approval")
        self.sessions.transition_task("task-resume", "executing")
        self.sessions.transition_task("task-resume", "failed", reason="child_interrupted")
        self.identity = self.resume.create("s-resume", "task-resume", "agent-a", str(root / "workspaces" / "task-resume"), ("read",), delegation_id="task-resume")
        self.resume.checkpoint("task-resume", "step-1")
        self.resume.mark_interrupted("task-resume")
        self.bridge = TaskExecutionBridge(self.sessions, self.actions, self.executor, delegated_resume_store=self.resume)
        self.bridge.register_action("task-resume", "delegated resume")

    def tearDown(self):
        self.tmp.cleanup()

    def test_bridge_requires_explicit_fresh_approval_before_resume(self):
        request = TaskExecutionRequest("task-resume", "agent-a", "task-resume")
        with self.assertRaisesRegex(TaskExecutionBridgeError, "fresh_resume_approval_required"):
            self.bridge.resume_delegated("s-resume", [request], lambda _: {"ok": True}, approval_ids={}, request_digests={})
        approval = self.resume.approve_resume("task-resume", "operator-approval")
        events = []
        report = self.bridge.resume_delegated("s-resume", [request], lambda _: {"ok": True}, approval_ids={"task-resume": approval}, request_digests={"task-resume": self.identity.request_digest}, event_sink=events.append)
        self.assertEqual(report.results[0].status, "passed")
        self.assertIn("delegation_resume_approved", {event["kind"] for event in events})
        with self.assertRaisesRegex(TaskExecutionBridgeError, "resume_approval_replayed"):
            self.bridge.resume_delegated("s-resume", [request], lambda _: {"ok": True}, approval_ids={"task-resume": approval}, request_digests={"task-resume": self.identity.request_digest})

    def test_health_exposes_bounded_read_only_resume_status(self):
        server = HealthServer(delegated_resume_provider=lambda: {"status": "resuming", "approval_token": "must-not-leak", "active": 1})
        snapshot = server.telemetry_snapshot()
        self.assertEqual(snapshot["delegated_resume"]["status"], "resuming")
        self.assertEqual(snapshot["delegated_resume"]["approval_token"], "[REDACTED]")
        self.assertFalse(snapshot["delegated_resume"]["automatic_resume"])
        self.assertEqual(server.operator_snapshot()["execution_claim"], "read_only_snapshot")


if __name__ == "__main__":
    unittest.main()

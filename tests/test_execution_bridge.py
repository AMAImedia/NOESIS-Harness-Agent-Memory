import os
import tempfile
import unittest
from pathlib import Path

from noesis_harness.coordination import Actions
from noesis_harness.execution_bridge import TaskExecutionBridge, TaskExecutionBridgeError, TaskExecutionRequest
from noesis_harness.parallel_agent import SafeParallelExecutor
from noesis_harness.task_session_api import SCHEMA_VERSION, TaskSessionStore


class ExecutionBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.store = TaskSessionStore(str(root / "session_events.jsonl"))
        self.actions = Actions(str(root / "actions.db"))
        self.executor = SafeParallelExecutor(str(root / "workspaces"), max_concurrency=2)
        self.bridge = TaskExecutionBridge(self.store, self.actions, self.executor)
        self.session = self.store.create_session("lead", session_id="session-bridge")

    def tearDown(self):
        self.tmp.cleanup()

    def create_waiting_task(self, task_id, title):
        self.store.create_task(self.session.session_id, title, "agent", task_id=task_id)
        self.store.transition_task(task_id, "planned", reason="test_plan")
        self.store.dispatch({
            "schema_version": SCHEMA_VERSION,
            "command_id": "request-" + task_id,
            "command": "task.request_execution",
            "payload": {"task_id": task_id, "reason": "test_request"},
        })
        self.bridge.register_action(task_id, title)

    def test_approval_is_required_before_any_lane_starts(self):
        self.create_waiting_task("task-approval", "Approval")
        called = []
        with self.assertRaisesRegex(TaskExecutionBridgeError, "explicit_execution_approval_required"):
            self.bridge.execute(self.session.session_id, [TaskExecutionRequest("task-approval", "agent-a", "agent-a")], lambda _: called.append(True))
        self.assertEqual(called, [])
        self.assertEqual(self.store.task("task-approval").state, "waiting_approval")

    def test_success_and_failure_map_to_task_and_action_lifecycle(self):
        self.create_waiting_task("task-good", "Good")
        self.create_waiting_task("task-bad", "Bad")
        events = []

        def callback(ctx):
            if ctx.task_id == "task-bad":
                raise RuntimeError("simulated interruption")
            result_path = ctx.path("result.txt")
            result_path.write_text(ctx.agent_id, encoding="utf-8")
            return {"agent": ctx.agent_id, "workspace": str(ctx.workspace)}

        report = self.bridge.execute(
            self.session.session_id,
            [TaskExecutionRequest("task-good", "agent-good", "good"), TaskExecutionRequest("task-bad", "agent-bad", "bad")],
            callback,
            approval=True,
            event_sink=events.append,
        )
        by_task = {result.task_id: result for result in report.results}
        self.assertEqual(by_task["task-good"].status, "passed")
        self.assertEqual(by_task["task-bad"].status, "failed")
        self.assertEqual(self.store.task("task-good").state, "review")
        self.assertEqual(self.store.task("task-bad").state, "failed")
        self.assertEqual(self.actions.counts().get("done"), 1)
        self.assertEqual(self.actions.counts().get("pending"), 1)
        kinds = {event["kind"] for event in events}
        self.assertTrue({"lane_started", "lane_claimed", "lane_completed", "lane_failed", "task_review_ready", "task_failed"}.issubset(kinds))
        for event in events:
            self.assertNotIn("workspace", event)
            self.assertNotIn("output", event)
            self.assertEqual(event["session_id"], self.session.session_id)

    def test_session_mismatch_fails_before_execution(self):
        self.create_waiting_task("task-mismatch", "Mismatch")
        with self.assertRaisesRegex(TaskExecutionBridgeError, "task_session_mismatch"):
            self.bridge.execute("other-session", [TaskExecutionRequest("task-mismatch", "agent", "mismatch")], lambda _: None, approval=True)
        self.assertEqual(self.store.task("task-mismatch").state, "waiting_approval")


if __name__ == "__main__":
    unittest.main(verbosity=2)

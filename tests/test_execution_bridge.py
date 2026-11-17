import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from noesis_harness.coordination import Actions
from noesis_harness.execution_bridge import TaskExecutionBridge, TaskExecutionBridgeError, TaskExecutionRequest
from noesis_harness.learning_promotion import LearningPromotionPipeline
from noesis_harness.promotion_integration import EvaluatorRegistry, PromotionEventBridge, PromotionIntegration, RuntimePolicySimulator
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

    def test_runtime_backed_lane_requires_verified_receipt_and_exposes_metadata_only(self):
        self.create_waiting_task("task-runtime", "Runtime")
        events = []

        class Runtime:
            def __init__(self, request_id):
                self.receipt_store = SimpleNamespace(get=lambda receipt_id: SimpleNamespace(receipt_id=receipt_id, outcome="committed"))
                self.request_id = request_id

            def run(self, request):
                Path(request.workspace, "runtime.txt").write_text("runtime output", encoding="utf-8")
                return SimpleNamespace(status="completed", request_id=self.request_id, sandboxed=True, receipt=SimpleNamespace(receipt_id="receipt-" + self.request_id, outcome="committed"))

        def factory(context):
            request_id = "exec-" + context.task_id
            return Runtime(request_id), SimpleNamespace(workspace=str(context.workspace), request_id=request_id)

        report = self.bridge.execute_runtime(self.session.session_id, [TaskExecutionRequest("task-runtime", "agent-runtime", "runtime-lane")], factory, approval=True, event_sink=events.append)
        self.assertEqual(report.results[0].status, "passed")
        self.assertEqual(self.store.task("task-runtime").state, "review")
        self.assertEqual(report.results[0].output["execution"]["receipt_id"], "receipt-exec-task-runtime")
        for event in events:
            self.assertNotIn("runtime output", repr(event))
            self.assertNotIn("receipt_store", repr(event))
        resumed = self.store.resume(self.session.session_id)
        self.assertEqual(resumed["execution_evidence"]["task-runtime"]["receipt_id"], "receipt-exec-task-runtime")
        reopened = TaskSessionStore(str(Path(self.tmp.name) / "session_events.jsonl"))
        reopened_bridge = TaskExecutionBridge(reopened, self.actions, self.executor)
        with self.assertRaisesRegex(TaskExecutionBridgeError, "task_not_waiting_approval:review"):
            reopened_bridge.execute_runtime(self.session.session_id, [TaskExecutionRequest("task-runtime", "agent-runtime", "runtime-lane")], factory, approval=True)

    def test_runtime_backed_lane_rejects_workspace_mismatch_before_child_run(self):
        self.create_waiting_task("task-runtime-mismatch", "Runtime mismatch")
        called = []

        def factory(context):
            return SimpleNamespace(run=lambda _: called.append(True)), SimpleNamespace(workspace=str(Path(self.tmp.name)), request_id="exec-mismatch")

        report = self.bridge.execute_runtime(self.session.session_id, [TaskExecutionRequest("task-runtime-mismatch", "agent-runtime", "runtime-lane-mismatch")], factory, approval=True)
        self.assertEqual(report.results[0].status, "failed")
        self.assertIn("runtime_workspace_mismatch", report.results[0].error)
        self.assertEqual(called, [])
        self.assertEqual(self.store.task("task-runtime-mismatch").state, "failed")

    def test_operator_trigger_is_required_and_runtime_policy_wiring_is_capture_only(self):
        pipeline = LearningPromotionPipeline(str(Path(self.tmp.name) / "promotion"), b"execution-bridge-key")
        integration = PromotionIntegration(pipeline, registry=EvaluatorRegistry())
        promotion_bridge = PromotionEventBridge(integration, str(Path(self.tmp.name) / "promotion-checkpoints.jsonl"))
        simulator = RuntimePolicySimulator("agent-runtime", "project:demo", allowed_scopes=("project:demo",))
        wired = TaskExecutionBridge(self.store, self.actions, self.executor, promotion_bridge=promotion_bridge, policy_simulator=simulator.simulate)
        with self.assertRaisesRegex(TaskExecutionBridgeError, "explicit_promotion_poll_trigger_required"):
            wired.poll_promotion_events()
        with self.assertRaisesRegex(TaskExecutionBridgeError, "promotion_runtime_not_configured"):
            self.bridge.poll_promotion_events(operator_trigger=True)
        self.store.create_task(self.session.session_id, "Promote", "agent-runtime", task_id="task-promote")
        self.store.transition_task("task-promote", "planned")
        self.store.transition_task("task-promote", "executing")
        self.store.transition_task("task-promote", "review")
        self.store.transition_task("task-promote", "committed")
        outcomes = wired.poll_promotion_events(operator_trigger=True)
        self.assertEqual(outcomes[0]["status"], "completed")
        self.assertEqual(len(pipeline._receipts), 1)
        self.assertFalse(integration.snapshot()["automatic_activation"])

    def test_session_mismatch_fails_before_execution(self):
        self.create_waiting_task("task-mismatch", "Mismatch")
        with self.assertRaisesRegex(TaskExecutionBridgeError, "task_session_mismatch"):
            self.bridge.execute("other-session", [TaskExecutionRequest("task-mismatch", "agent", "mismatch")], lambda _: None, approval=True)
        self.assertEqual(self.store.task("task-mismatch").state, "waiting_approval")


if __name__ == "__main__":
    unittest.main(verbosity=2)

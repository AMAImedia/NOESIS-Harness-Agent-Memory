import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from noesis_harness.coordination import Actions
from noesis_harness.delegated_resume import DelegatedResumeStore
from noesis_harness.delegated_resume_action import DelegatedResumeAction, DelegatedResumeActionExecutor, bridge_runtime_resume_callback
from noesis_harness.execution_bridge import TaskExecutionBridge, TaskExecutionRequest
from noesis_harness.parallel_agent import SafeParallelExecutor
from noesis_harness.task_session_api import TaskSessionStore


class DelegatedResumeE2ETests(unittest.TestCase):
    def test_signed_operator_resume_reaches_normal_bridge_and_runtime_receipt_gates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sessions = TaskSessionStore(str(root / "sessions.jsonl"))
            actions = Actions(str(root / "actions.db"))
            executor = SafeParallelExecutor(str(root / "workspaces"), max_concurrency=1)
            delegations = DelegatedResumeStore(str(root / "delegations.jsonl"))
            session = sessions.create_session("operator", session_id="session-e2e")
            sessions.create_task(session.session_id, "resume runtime", "agent", task_id="task-e2e")
            for state in ("planned", "waiting_approval", "executing", "failed"):
                sessions.transition_task("task-e2e", state, reason="fixture", command_id="fixture-" + state)
            bridge = TaskExecutionBridge(sessions, actions, executor, delegated_resume_store=delegations)
            bridge.register_action("task-e2e", "resume runtime")
            identity = delegations.create(session.session_id, "task-e2e", "agent-e2e", str(root / "workspaces" / "task-e2e"), ("read",), delegation_id="task-e2e")
            delegations.checkpoint("task-e2e", "before-runtime")
            delegations.mark_interrupted("task-e2e")
            approval_id = delegations.approve_resume("task-e2e", "operator-approval-e2e")
            request = TaskExecutionRequest("task-e2e", "agent-e2e", "task-e2e")

            class Runtime:
                def __init__(self):
                    self.receipt_store = SimpleNamespace(get=lambda receipt_id: SimpleNamespace(receipt_id=receipt_id, outcome="committed"))

                def run(self, _request):
                    return SimpleNamespace(status="completed", request_id="request-e2e", sandboxed=True, receipt=SimpleNamespace(receipt_id="receipt-e2e", outcome="committed"))

            def runtime_factory(_context):
                runtime = Runtime()
                return runtime, SimpleNamespace(workspace=str(root / "workspaces" / "task-e2e"), request_id="request-e2e")

            action = DelegatedResumeAction.sign(action_id="action-e2e", operator_id="operator-1", session_id=session.session_id, task_id="task-e2e", approval_id=approval_id, request_digest=identity.request_digest, signing_key=b"operator-signing-key-1234")
            handler = DelegatedResumeActionExecutor(str(root / "resume-audit.jsonl"), signing_key=b"operator-signing-key-1234", resume_callback=bridge_runtime_resume_callback(bridge, request, runtime_factory))
            result = handler.handle(action, SimpleNamespace(authenticated=True, operator_id="operator-1", scopes=("task:resume",)))
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["result"]["status"], "passed")
            self.assertEqual(sessions.task("task-e2e").state, "review")
            self.assertEqual(actions.counts().get("done"), 1)
            self.assertEqual(handler.handle(action, SimpleNamespace(authenticated=True, operator_id="operator-1", scopes=("task:resume",)))["status"], "replayed")


if __name__ == "__main__":
    unittest.main()

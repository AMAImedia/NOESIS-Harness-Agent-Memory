import json
import tempfile
import unittest
import urllib.request
from pathlib import Path
from types import SimpleNamespace

from noesis_harness.delegated_resume_action import DelegatedResumeAction, DelegatedResumeActionError, DelegatedResumeActionExecutor
from noesis_harness.health_server import HealthServer


class DelegatedResumeActionTests(unittest.TestCase):
    def _executor(self, callback):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        return DelegatedResumeActionExecutor(str(Path(directory.name) / "actions.jsonl"), signing_key=b"operator-signing-key-1234", resume_callback=callback)

    def _action(self, signature_key=b"operator-signing-key-1234"):
        return DelegatedResumeAction.sign(action_id="resume-action-1", operator_id="operator-1", session_id="session-1", task_id="task-1", approval_id="approval-1", request_digest="a" * 64, signing_key=signature_key)

    def test_valid_action_runs_once_and_receipt_is_signed(self):
        calls = []
        executor = self._executor(lambda action: calls.append(action.task_id) or {"status": "resumed"})
        context = SimpleNamespace(authenticated=True, operator_id="operator-1", scopes=("task:resume",))
        result = executor.handle(self._action(), context)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(calls, ["task-1"])
        self.assertEqual(result["audit_receipt"]["schema_version"], "noesis.delegated-resume-receipt.v1")
        replay = executor.handle(self._action(), context)
        self.assertEqual(replay["status"], "replayed")
        self.assertEqual(calls, ["task-1"])

    def test_signature_tamper_and_scope_denial_stop_before_callback(self):
        calls = []
        executor = self._executor(lambda action: calls.append(True) or {})
        context = SimpleNamespace(authenticated=True, operator_id="operator-1", scopes=("task:resume",))
        action = self._action()
        tampered = DelegatedResumeAction(action.action_id, action.operator_id, action.session_id, action.task_id, action.approval_id, "b" * 64, action.signature)
        with self.assertRaisesRegex(DelegatedResumeActionError, "signature_invalid"):
            executor.handle(tampered, context)
        denied = SimpleNamespace(authenticated=True, operator_id="operator-1", scopes=("task:read",))
        with self.assertRaisesRegex(DelegatedResumeActionError, "scope_required"):
            executor.handle(self._action(), denied)
        self.assertEqual(calls, [])

    def test_authenticated_http_endpoint_dispatches_signed_action(self):
        calls = []
        executor = self._executor(lambda action: calls.append(action.action_id) or {"status": "resumed", "approval_token": "hidden"})
        action = self._action()
        with HealthServer(port=0, delegated_resume_action_handler=executor.handle, operator_id="operator-1", operator_session_id="session-1", operator_scopes=("task:resume",)) as server:
            request = urllib.request.Request("http://127.0.0.1:%d/api/delegated-resume" % server.bound_port, data=json.dumps(action.to_mapping()).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(request, timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(payload["ok"], True)
            self.assertEqual(payload["data"]["result"]["status"], "completed")
            self.assertEqual(payload["data"]["result"]["result"]["approval_token"], "[REDACTED]")
        self.assertEqual(calls, ["resume-action-1"])

    def test_operator_identity_and_missing_auth_are_denied(self):
        executor = self._executor(lambda action: {"status": "bad"})
        with self.assertRaisesRegex(DelegatedResumeActionError, "operator_identity_mismatch"):
            executor.handle(self._action(), SimpleNamespace(authenticated=True, operator_id="other", scopes=("task:resume",)))
        with self.assertRaisesRegex(DelegatedResumeActionError, "operator_identity_mismatch"):
            executor.handle(self._action(), SimpleNamespace(authenticated=False, operator_id="operator-1", scopes=("task:resume",)))


if __name__ == "__main__":
    unittest.main()

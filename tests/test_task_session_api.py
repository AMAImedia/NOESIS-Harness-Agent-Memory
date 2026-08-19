import tempfile
import unittest
from pathlib import Path

from noesis_harness.task_session_api import TaskSessionError, TaskSessionStore


class TaskSessionApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = TaskSessionStore(str(Path(self.tmp.name) / "events.jsonl"))
        self.session = self.store.create_session("agent-lead", session_id="sess-test")
        self.task = self.store.create_task("sess-test", "Review release", "agent-a", task_id="task-test")

    def tearDown(self):
        self.tmp.cleanup()

    def test_idempotent_create_does_not_duplicate(self):
        self.store.create_session("agent-lead", session_id="sess-test", command_id="create-session-sess-test")
        self.assertEqual(self.store.events.count(), 2)

    def test_state_machine_and_resume(self):
        self.store.transition_task("task-test", "planned")
        self.store.transition_task("task-test", "waiting_approval")
        self.store.transition_task("task-test", "executing")
        self.store.append_message("sess-test", "assistant", "token=ghp_1234567890 should not persist")
        resumed = self.store.resume("sess-test")
        self.assertEqual(resumed["tasks"][0].state, "executing")
        self.assertIn("[REDACTED]", resumed["messages"][0]["content"])
        self.assertNotIn("ghp_1234567890", str(resumed))

    def test_execution_evidence_survives_reopen_and_replay_is_idempotent(self):
        evidence = {"request_id": "exec-1", "receipt_id": "receipt-1", "outcome": "committed", "sandboxed": True, "stdout": "secret output"}
        first = self.store.record_execution_evidence("sess-test", "task-test", evidence)
        second = self.store.record_execution_evidence("sess-test", "task-test", evidence)
        self.assertEqual(first["receipt_id"], "receipt-1")
        self.assertEqual(second["request_id"], "exec-1")
        reopened = TaskSessionStore(str(Path(self.tmp.name) / "events.jsonl"))
        resumed = reopened.resume("sess-test")
        self.assertEqual(resumed["execution_evidence"]["task-test"]["receipt_id"], "receipt-1")
        self.assertNotIn("secret output", str(resumed))
        self.assertEqual(reopened.events.count(), self.store.events.count())

    def test_execution_evidence_conflict_and_session_mismatch_fail_closed(self):
        self.store.record_execution_evidence("sess-test", "task-test", {"request_id": "exec-1", "receipt_id": "receipt-1", "outcome": "committed", "sandboxed": False})
        with self.assertRaisesRegex(TaskSessionError, "execution_evidence_conflict"):
            self.store.record_execution_evidence("sess-test", "task-test", {"request_id": "exec-1", "receipt_id": "receipt-2", "outcome": "committed", "sandboxed": False})
        with self.assertRaisesRegex(TaskSessionError, "task_session_mismatch"):
            self.store.record_execution_evidence("other-session", "task-test", {"request_id": "exec-2", "receipt_id": "receipt-2", "outcome": "committed"})

    def test_invalid_transition_fails_closed(self):
        with self.assertRaises(TaskSessionError):
            self.store.transition_task("task-test", "committed")

    def test_secret_keys_are_not_persisted(self):
        self.store.append_message("sess-test", "user", "hello", command_id="m1")
        self.store._append("session_metadata", {"session_id": "sess-test", "api_key": "should-drop", "note": "safe"}, "meta-1")
        serialized = Path(self.tmp.name, "events.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("should-drop", serialized)
        self.assertIn("safe", serialized)

    def test_resume_after_interrupted_tail_preserves_rollback_boundary(self):
        for target in ("planned", "waiting_approval", "executing", "review", "rolled_back"):
            self.store.transition_task("task-test", target)
        event_path = Path(self.tmp.name, "events.jsonl")
        with event_path.open("ab") as stream:
            stream.write(b'{"event_id":"partial","type":"task_state_changed","payload":')
        reopened = TaskSessionStore(str(event_path))
        resumed = reopened.resume("sess-test")
        self.assertEqual(resumed["tasks"][0].state, "rolled_back")
        self.assertEqual(reopened.events.count(), self.store.events.count())
        reopened.transition_task("task-test", "planned", reason="retry-after-rollback", command_id="retry-after-rollback")
        self.assertEqual(reopened.task("task-test").state, "planned")


if __name__ == "__main__":
    unittest.main()

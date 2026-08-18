import json
import tempfile
import unittest
import urllib.request
from pathlib import Path

from noesis_harness.health_server import HealthServer
from noesis_harness.task_session_api import SCHEMA_VERSION, TaskSessionError, TaskSessionStore


class CommandDispatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = TaskSessionStore(str(Path(self.tmp.name) / "events.jsonl"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_versioned_dispatch_is_idempotent_and_transitions(self):
        create = {
            "schema_version": SCHEMA_VERSION,
            "command_id": "cmd-session-1",
            "command": "session.create",
            "payload": {"owner": "lead"},
        }
        first = self.store.dispatch(create)
        second = self.store.dispatch(create)
        self.assertEqual(first["result"].session_id, second["result"].session_id)
        self.assertEqual(self.store.events.count(), 1)
        session_id = first["result"].session_id
        task = self.store.dispatch({
            "schema_version": SCHEMA_VERSION,
            "command_id": "cmd-task-1",
            "command": "task.create",
            "payload": {"session_id": session_id, "title": "Inspect", "owner": "agent-a"},
        })
        task_id = task["result"].task_id
        planned = self.store.dispatch({
            "schema_version": SCHEMA_VERSION,
            "command_id": "cmd-transition-1",
            "command": "task.transition",
            "payload": {"task_id": task_id, "target": "planned"},
        })
        self.assertEqual(planned["result"].state, "planned")

    def test_invalid_schema_and_transition_fail_closed(self):
        with self.assertRaisesRegex(TaskSessionError, "unsupported_command_schema"):
            self.store.dispatch({"schema_version": "noesis.task-session.v0", "command_id": "x", "command": "session.create", "payload": {"owner": "x"}})
        session = self.store.create_session("lead", session_id="s")
        task = self.store.create_task(session.session_id, "Inspect", "agent")
        with self.assertRaises(TaskSessionError):
            self.store.dispatch({"schema_version": SCHEMA_VERSION, "command_id": "bad-transition", "command": "task.transition", "payload": {"task_id": task.task_id, "target": "committed"}})

    def test_command_message_redacts_credentials(self):
        session = self.store.create_session("lead", session_id="s")
        result = self.store.dispatch({
            "schema_version": SCHEMA_VERSION,
            "command_id": "cmd-message-1",
            "command": "session.message",
            "payload": {"session_id": session.session_id, "role": "user", "content": "token=ghp_1234567890 do not persist"},
        })
        self.assertEqual(result["result"]["session_id"], session.session_id)
        self.assertIn("[REDACTED]", self.store.messages(session.session_id)[0]["content"])


class CommandHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = TaskSessionStore(str(Path(self.tmp.name) / "events.jsonl"))

    def tearDown(self):
        self.tmp.cleanup()

    def request(self, base, path, method="GET", payload=None, headers=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(base + path, data=data, method=method, headers={"Content-Type": "application/json", **(headers or {})})
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status, json.loads(response.read().decode("utf-8")) if response.headers.get("Content-Type", "").startswith("application/json") else response.read().decode("utf-8")

    def test_command_route_task_route_and_sse(self):
        with HealthServer(port=0, session_store=self.store) as server:
            base = "http://127.0.0.1:%d" % server.address[1]
            status, created = self.request(base, "/api/commands", "POST", {"schema_version": SCHEMA_VERSION, "command_id": "http-session", "command": "session.create", "payload": {"owner": "ui"}})
            self.assertEqual(status, 202)
            session_id = created["data"]["command"]["result"]["session_id"]
            status, task_result = self.request(base, "/api/commands", "POST", {"schema_version": SCHEMA_VERSION, "command_id": "http-task", "command": "task.create", "payload": {"session_id": session_id, "title": "Review", "owner": "agent"}})
            self.assertEqual(status, 202)
            task_id = task_result["data"]["command"]["result"]["task_id"]
            status, task_payload = self.request(base, "/api/tasks/" + task_id)
            self.assertEqual(status, 200)
            self.assertEqual(task_payload["data"]["task"]["task_id"], task_id)
            status, stream = self.request(base, "/api/sessions/" + session_id + "/events")
            self.assertEqual(status, 200)
            self.assertIn("event: command", stream)
            self.assertIn('"sequence":1', stream)
            self.assertIn('"sequence":2', stream)

    def test_default_server_rejects_command_route(self):
        with HealthServer(port=0) as server:
            base = "http://127.0.0.1:%d" % server.address[1]
            request = urllib.request.Request(base + "/api/commands", data=b"{}", method="POST", headers={"Content-Type": "application/json"})
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(request, timeout=2)
            ctx.exception.close()
            self.assertEqual(ctx.exception.code, 405)


if __name__ == "__main__":
    unittest.main(verbosity=2)

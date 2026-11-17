import tempfile
import unittest
from pathlib import Path

from noesis_harness.health_server import HealthServer
from noesis_harness.task_session_api import TaskSessionStore
from noesis_harness.terminal_client import SessionClient


class TerminalClientTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = TaskSessionStore(str(Path(self.tmp.name) / "events.jsonl"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_create_send_resume_uses_versioned_api(self):
        with HealthServer(port=0, session_store=self.store) as server:
            client = SessionClient("http://127.0.0.1:%d" % server.address[1])
            created = client.create("terminal-user")
            session_id = created["data"]["session"]["session_id"]
            sent = client.send(session_id, "hello")
            self.assertEqual(sent["status"], "ready")
            resumed = client.resume(session_id)
            self.assertEqual(resumed["data"]["session"]["owner"], "terminal-user")
            self.assertEqual(resumed["data"]["messages"][0]["content"], "hello")


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
import urllib.request
from pathlib import Path

from noesis_harness.health_server import HealthServer
from noesis_harness.task_session_api import TaskSessionStore


class HealthSessionApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = TaskSessionStore(str(Path(self.tmp.name) / "events.jsonl"))

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def _request(url, method="GET", payload=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {} if data is None else {"Content-Type": "application/json"}
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def test_session_create_message_resume_and_events(self):
        with HealthServer(port=0, session_store=self.store) as server:
            base = "http://127.0.0.1:%d" % server.address[1]
            status, created = self._request(base + "/api/sessions", "POST", {"owner": "local-user"})
            self.assertEqual(status, 201)
            session_id = created["data"]["session"]["session_id"]
            status, message = self._request(base + "/api/sessions/" + session_id + "/messages", "POST", {"role": "user", "content": "hello token=secret-value"})
            self.assertEqual(status, 201)
            self.assertEqual(message["status"], "ready")
            status, resumed = self._request(base + "/api/sessions/" + session_id)
            self.assertEqual(status, 200)
            self.assertEqual(resumed["data"]["session"]["session_id"], session_id)
            self.assertIn("[REDACTED]", resumed["data"]["messages"][0]["content"])
            request = urllib.request.Request(base + "/api/sessions/" + session_id + "/events", method="GET")
            with urllib.request.urlopen(request, timeout=2) as response:
                status = response.status
                events = response.read().decode("utf-8")
            self.assertEqual(status, 200)
            self.assertIn("event: message", events)

    def test_default_server_remains_read_only(self):
        with HealthServer(port=0) as server:
            base = "http://127.0.0.1:%d" % server.address[1]
            request = urllib.request.Request(base + "/api/sessions", data=b"{}", method="POST")
            with self.assertRaises(Exception):
                urllib.request.urlopen(request, timeout=2)


if __name__ == "__main__":
    unittest.main()

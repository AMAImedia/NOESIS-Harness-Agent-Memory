import json
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from noesis_harness.health_server import HealthServer


class LifecycleIngestionHealthTests(unittest.TestCase):
    def post(self, server, payload):
        request = urllib.request.Request("http://127.0.0.1:%d/api/lifecycle-audit-ingestion" % server.bound_port, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
        return urllib.request.urlopen(request, timeout=2)

    def test_readiness_and_snapshot_projection_are_bounded(self):
        server = HealthServer(lifecycle_ingestion_status_provider=lambda: {"schema_version": "noesis.lifecycle-audit-ingestion.v1", "state": "approved", "execution_allowed": True, "automatic_import": True, "claim": True, "operator_token": "secret"})
        item = server.operator_snapshot()["lifecycle_ingestion"]
        self.assertEqual(item["state"], "approved")
        self.assertFalse(item["execution_allowed"])
        self.assertFalse(item["automatic_import"])
        self.assertFalse(item["claim"])
        self.assertEqual(item["operator_token"], "[REDACTED]")

    def test_endpoint_requires_scope_and_dispatches_operator_action(self):
        calls = []
        def handler(payload, context):
            calls.append((payload["action"], context.operator_id))
            return {"state": "awaiting_approval", "automatic_import": True, "claim": True}
        payload = {"schema_version": "noesis.lifecycle-audit-ingestion-action.v1", "action": "preflight"}
        denied = HealthServer(port=0, lifecycle_ingestion_action_handler=handler, operator_id="op", operator_session_id="sess", operator_scopes=())
        with denied:
            with self.assertRaises(urllib.error.HTTPError) as caught:
                self.post(denied, payload)
            self.assertEqual(caught.exception.code, 403)
            caught.exception.close()
        allowed = HealthServer(port=0, lifecycle_ingestion_action_handler=handler, operator_id="op", operator_session_id="sess", operator_scopes=("lifecycle:audit:write",))
        with allowed:
            with self.post(allowed, payload) as response:
                body = json.loads(response.read().decode())
            self.assertTrue(body["ok"])
            self.assertFalse(body["data"]["result"]["automatic_import"])
            self.assertEqual(body["data"]["result"]["control"], "operator_approval_required")
        self.assertEqual(calls, [("preflight", "op")])


if __name__ == "__main__":
    unittest.main()

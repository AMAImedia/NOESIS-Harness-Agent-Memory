import json
import threading
import time
import unittest
import urllib.error
import urllib.request

from noesis_harness.health_server import HealthServer
from noesis_harness.ui_contract import CONTRACT_VERSION, UIContractError, failure, health_payload, model_payload, success


class UIContractTests(unittest.TestCase):
    def test_success_redacts_secrets_and_is_deterministic(self):
        envelope = success({"model": "local", "api_key": "secret-value", "nested": {"password": "hidden"}}, request_id="fixed")
        payload = envelope.to_dict()
        self.assertEqual(payload["contract_version"], CONTRACT_VERSION)
        self.assertEqual(payload["data"]["api_key"], "[REDACTED]")
        self.assertEqual(payload["data"]["nested"]["password"], "[REDACTED]")
        self.assertEqual(envelope.to_json(), envelope.to_json())
        self.assertNotIn("secret-value", envelope.to_json())

    def test_health_degraded_when_optional_capabilities_are_unavailable(self):
        envelope = health_payload(
            runtime_version="0.1",
            readiness="ready",
            binding="127.0.0.1:0",
            capabilities={"ui_contract": "ready", "hermes_adapter": "unavailable"},
            unavailable_reasons=("hermes_adapter_unavailable",),
        )
        self.assertEqual(envelope.status, "degraded")
        self.assertEqual(envelope.data["readiness"], "ready")

    def test_models_require_id_provider_and_valid_status(self):
        envelope = model_payload(({"id": "m", "provider": "ollama", "capabilities": {"tools": False}},))
        self.assertEqual(envelope.data["models"][0]["id"], "m")
        with self.assertRaises(UIContractError):
            model_payload(({"provider": "ollama"},))
        with self.assertRaises(UIContractError):
            success(status="not-a-status")
        with self.assertRaises(UIContractError):
            failure("ready", "bad", "bad")


class HealthServerTests(unittest.TestCase):
    def _request(self, method, path):
        request = urllib.request.Request(path, method=method)
        try:
            with urllib.request.urlopen(request, timeout=2) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            payload = json.loads(error.read().decode("utf-8"))
            error.close()
            return error.code, payload

    def test_loopback_health_response_and_clean_shutdown(self):
        server = HealthServer(runtime_version="test", port=0)
        address = server.start()
        try:
            self.assertEqual(address[0], "127.0.0.1")
            code, payload = self._request("GET", f"http://{address[0]}:{address[1]}/health")
            self.assertEqual(code, 200)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["contract_version"], CONTRACT_VERSION)
            self.assertEqual(payload["data"]["readiness"], "ready")
        finally:
            server.stop()
        self.assertEqual(server._thread, None)

    def test_read_only_and_unknown_path_fail_soft(self):
        with HealthServer(port=0) as server:
            address = server.address
            code, payload = self._request("POST", f"http://{address[0]}:{address[1]}/health")
            self.assertEqual(code, 405)
            self.assertEqual(payload["status"], "denied")
            code, payload = self._request("GET", f"http://{address[0]}:{address[1]}/not-found")
            self.assertEqual(code, 404)
            self.assertEqual(payload["status"], "invalid_request")

    def test_telemetry_snapshot_child_runtime_and_sse_are_read_only(self):
        server = HealthServer(port=0)
        server.set_telemetry(
            streams=({"stream_id": "s-1", "state": "active", "api_key": "hidden"},),
            child_runtimes=({"runtime_id": "child-1", "state": "running", "pid": 123},),
            counters={"events": 4},
        )
        with server:
            base = f"http://{server.address[0]}:{server.address[1]}"
            code, payload = self._request("GET", base + "/api/telemetry")
            self.assertEqual(code, 200)
            self.assertEqual(payload["data"]["telemetry"]["counters"]["active_streams"], 1)
            self.assertEqual(payload["data"]["telemetry"]["streams"][0]["api_key"], "[REDACTED]")
            code, child_payload = self._request("GET", base + "/api/child-runtimes")
            self.assertEqual(code, 200)
            self.assertEqual(child_payload["data"]["telemetry"]["child_runtimes"][0]["runtime_id"], "child-1")
            request = urllib.request.Request(base + "/api/telemetry/events", method="GET")
            with urllib.request.urlopen(request, timeout=2) as response:
                body = response.read().decode("utf-8")
                self.assertEqual(response.headers["Content-Type"], "text/event-stream; charset=utf-8")
                self.assertIn("event: telemetry", body)
                self.assertIn('"runtime_id":"child-1"', body)
                self.assertNotIn("hidden", body)

    def test_operator_promotion_action_requires_handler_and_returns_contract(self):
        action_payload = {"schema_version": "noesis.promotion-approval.v1", "action_id": "action-1", "action": "approve", "proposal_id": "proposal-1", "operator_id": "operator-1"}
        with HealthServer(port=0) as server:
            base = f"http://{server.address[0]}:{server.address[1]}"
            request = urllib.request.Request(base + "/api/promotion-actions", data=json.dumps(action_payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
            with self.assertRaises(urllib.error.HTTPError) as context:
                urllib.request.urlopen(request, timeout=2)
            error = context.exception
            try:
                payload = json.loads(error.read().decode("utf-8"))
            finally:
                error.close()
            self.assertEqual(error.code, 405)
            self.assertEqual(payload["error"]["code"], "promotion_actions_unavailable")

        handled = []
        with HealthServer(port=0, promotion_action_handler=lambda action, context: handled.append((action.to_mapping(), context)) or {"status": "queued"}, operator_id="operator-1", operator_session_id="session-1", operator_scopes=("promotion:approve",)) as server:
            base = f"http://{server.address[0]}:{server.address[1]}"
            request = urllib.request.Request(base + "/api/promotion-actions", data=json.dumps(action_payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(request, timeout=2) as response:
                self.assertEqual(response.status, 202)
                payload = json.loads(response.read().decode("utf-8"))
                self.assertEqual(payload["data"]["action"]["proposal_id"], "proposal-1")
                self.assertEqual(payload["data"]["result"]["status"], "queued")
        self.assertEqual(handled[0][0]["action"], "approve")
        self.assertEqual(handled[0][1].operator_id, "operator-1")
        self.assertEqual(handled[0][1].session_id, "session-1")

    def test_duplicate_start_and_invalid_binding_are_safe(self):
        with HealthServer(port=0) as server:
            first = server.start()
            second = server.start()
            self.assertEqual(first, second)
        with self.assertRaises(ValueError):
            HealthServer(host="0.0.0.0")
        with self.assertRaises(ValueError):
            HealthServer(max_request_bytes=128)


if __name__ == "__main__":
    unittest.main()

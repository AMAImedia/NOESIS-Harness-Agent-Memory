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
            return error.code, json.loads(error.read().decode("utf-8"))

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

import tempfile
import unittest
from pathlib import Path

from noesis_harness.gateway_runtime import GatewayRequest, GatewayRouter, ProviderRoute
from noesis_harness.resource_lineage import Observation, ObservationLedger


class GatewayRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        ledger = ObservationLedger(str(Path(self.tmp.name) / "events.jsonl"))
        ledger.record(Observation("s", "a", "public:doc", "docs", "public"))
        self.gateway = GatewayRouter(ledger=ledger, max_payload_bytes=128)
        self.gateway.register(ProviderRoute("local", "http://127.0.0.1:9000", ("chat",), ("deepseek-local",), "ready", "loopback"))
        self.gateway.register(ProviderRoute("remote", "https://provider.invalid", ("chat",), ("deepseek-api",), "unknown", "external"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_loopback_transport_requires_injected_transport_and_updates_health(self):
        request = GatewayRequest("s", "a", "local", "deepseek-local", "chat", {"messages": []})
        response = self.gateway.route(request, lambda route, body: {"text": "ok", "route": route.provider_id})
        self.assertTrue(response.ok)
        self.assertEqual(response.data["route"], "local")
        self.assertEqual(self.gateway.health_snapshot()["providers"][0]["health"]["status"], "ready")

    def test_external_requires_explicit_approval(self):
        request = GatewayRequest("s", "a", "remote", "deepseek-api", "chat", {"messages": []})
        denied = self.gateway.route(request, lambda route, body: {"ok": True})
        self.assertFalse(denied.ok)
        self.assertEqual(denied.reason, "external_network_requires_approval")
        allowed = self.gateway.route(request.__class__(**{**request.__dict__, "explicit_approval": True}), lambda route, body: {"ok": True})
        self.assertTrue(allowed.ok)

    def test_capability_model_and_payload_guards(self):
        base = GatewayRequest("s", "a", "local", "deepseek-local", "tools", {})
        self.assertEqual(self.gateway.route(base).reason, "capability_not_supported")
        wrong_model = GatewayRequest("s", "a", "local", "unknown", "chat", {})
        self.assertEqual(self.gateway.route(wrong_model).reason, "model_not_pinned")
        oversized = GatewayRequest("s", "a", "local", "deepseek-local", "chat", {"x": "a" * 200})
        self.assertEqual(self.gateway.route(oversized).reason, "payload_budget_exceeded")


if __name__ == "__main__":
    unittest.main()

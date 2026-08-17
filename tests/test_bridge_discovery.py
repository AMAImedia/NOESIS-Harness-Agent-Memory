import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from noesis_harness.bridge_discovery import BridgeCandidate, BridgeDiscovery
from noesis_harness.provider_registry import ModelDescriptor, ProviderDescriptor, ProviderRegistry
from noesis_harness.health_server import HealthServer


class BridgeDiscoveryTests(unittest.TestCase):
    def test_ready_hermes_capability_and_matching_model(self):
        registry = ProviderRegistry((ProviderDescriptor(provider_id="hermes-local", kind="hermes_webui", status="ready", models=(ModelDescriptor(model_id="hermes-model", provider="hermes_webui"),)),))
        with HealthServer(port=0, capabilities={"ui_contract": "ready", "hermes_webui": "ready", "deepseek_harness": "unavailable"}, provider_registry=registry) as server:
            candidate = BridgeCandidate("hermes", "hermes_webui", f"http://{server.address[0]}:{server.address[1]}")
            status = BridgeDiscovery((candidate,)).discover()[0]
            self.assertEqual(status.status, "ready")
            self.assertEqual(status.reason, "verified")
            self.assertEqual(status.model_count, 1)

    def test_missing_deepseek_is_explicitly_unavailable(self):
        with HealthServer(port=0) as server:
            candidate = BridgeCandidate("deepseek", "deepseek_harness", f"http://{server.address[0]}:{server.address[1]}")
            status = BridgeDiscovery((candidate,)).discover()[0]
            self.assertEqual(status.status, "unavailable")
            self.assertEqual(status.reason, "capability_unavailable")

    def test_unreachable_endpoint_is_fail_soft(self):
        status = BridgeDiscovery((BridgeCandidate("missing", "hermes_webui", "http://127.0.0.1:1", timeout_seconds=0.05),)).discover()[0]
        self.assertEqual(status.status, "unavailable")
        self.assertTrue(status.reason.startswith("probe_failed:"))

    def test_ready_capability_without_matching_model_is_degraded(self):
        registry = ProviderRegistry((ProviderDescriptor(provider_id="other", kind="openai_compatible", status="ready", models=(ModelDescriptor(model_id="other", provider="openai_compatible"),)),))
        with HealthServer(port=0, capabilities={"ui_contract": "ready", "hermes_webui": "ready"}, provider_registry=registry) as server:
            candidate = BridgeCandidate("hermes", "hermes_webui", f"http://{server.address[0]}:{server.address[1]}")
            status = BridgeDiscovery((candidate,)).discover()[0]
            self.assertEqual(status.status, "degraded")
            self.assertEqual(status.reason, "capability_ready_but_no_matching_models")


if __name__ == "__main__":
    unittest.main()

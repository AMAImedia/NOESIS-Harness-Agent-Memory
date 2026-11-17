import unittest

from noesis_harness.bridge_integration import BridgeIntegrationCoordinator
from noesis_harness.deepseek_harness import DeepSeekHarnessAdapter, DeepSeekHarnessConfig
from noesis_harness.hermes_gateway import HermesGatewayAdapter, HermesGatewayConfig


class BridgeIntegrationTests(unittest.TestCase):
    def configs(self):
        hermes = HermesGatewayAdapter(HermesGatewayConfig(
            gateway_id="hermes-local",
            base_url="http://127.0.0.1:1",
            pinned_version="2026.08.17",
            tool_scopes=("health.read", "models.read", "chat"),
        ))
        deepseek = DeepSeekHarnessAdapter(DeepSeekHarnessConfig(
            harness_id="deepseek-local",
            base_url="http://127.0.0.1:2",
            pinned_version="2026.08.17",
            plugin_id="memory",
            plugin_version="1.0.0",
            plugin_capabilities={"memory": ("long_context", "structured_output")},
        ))
        return hermes, deepseek

    def test_registration_is_metadata_only_and_deterministic(self):
        hermes, deepseek = self.configs()
        coordinator = BridgeIntegrationCoordinator()
        coordinator.register_deepseek(deepseek)
        coordinator.register_hermes(hermes)
        self.assertEqual([record.bridge_id for record in coordinator.records()], ["deepseek-local", "hermes-local"])
        self.assertNotIn("token", str(coordinator.metadata()).lower())
        self.assertEqual(coordinator.records()[0].candidate.base_url, "http://127.0.0.1:2")

    def test_discovery_is_explicit_and_unavailable_is_fail_soft(self):
        hermes, deepseek = self.configs()
        coordinator = BridgeIntegrationCoordinator()
        coordinator.register_hermes(hermes)
        coordinator.register_deepseek(deepseek)
        statuses = coordinator.discover()
        self.assertEqual(len(statuses), 2)
        self.assertTrue(all(status.status == "unavailable" for status in statuses))

    def test_hermes_scope_compatibility_and_deepseek_missing_capability(self):
        hermes, deepseek = self.configs()
        coordinator = BridgeIntegrationCoordinator()
        coordinator.register_hermes(hermes)
        coordinator.register_deepseek(deepseek)
        self.assertEqual(coordinator.compatibility("hermes-local", ("chat",)).status, "ready")
        self.assertEqual(coordinator.compatibility("hermes-local", ("tools.invoke",)).status, "degraded")
        self.assertEqual(coordinator.compatibility("deepseek-local", ("vision",)).reason, "deepseek_adapter_not_attached")

    def test_unknown_bridge_is_unavailable(self):
        result = BridgeIntegrationCoordinator().compatibility("missing", ("chat",))
        self.assertEqual(result.status, "unavailable")
        self.assertEqual(result.reason, "bridge_not_registered")


if __name__ == "__main__":
    unittest.main()

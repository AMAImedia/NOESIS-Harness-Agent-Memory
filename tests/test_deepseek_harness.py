import unittest

from noesis_harness.deepseek_harness import DeepSeekHarnessAdapter, DeepSeekHarnessConfig, DeepSeekHarnessError


class DeepSeekHarnessTests(unittest.TestCase):
    def config(self, **overrides):
        values = {
            "harness_id": "deepseek-local",
            "base_url": "http://127.0.0.1:9000",
            "pinned_version": "2026.08.17",
            "plugin_id": "noesis-plugin",
            "plugin_version": "1.2.0",
            "plugin_capabilities": {"memory": ("long_context",), "tools": ("tools", "structured_output")},
        }
        values.update(overrides)
        return DeepSeekHarnessConfig(**values)

    def test_plugin_mapping_and_ready_compatibility(self):
        adapter = DeepSeekHarnessAdapter(self.config())
        mapping = adapter.capability_mapping()
        self.assertEqual(mapping["tools"], ("tools",))
        result = adapter.compatibility(("tools", "long_context"))
        self.assertEqual(result.status, "ready")
        self.assertEqual(result.missing, ())
        self.assertEqual(adapter.status(), "ready")

    def test_missing_plugin_is_degraded_not_fake_ready(self):
        result = DeepSeekHarnessAdapter(self.config()).compatibility(("vision",))
        self.assertEqual(result.status, "degraded")
        self.assertEqual(result.reason, "missing_plugin_capability")
        self.assertEqual(result.missing, ("vision",))

    def test_unknown_contract_or_capability_is_incompatible(self):
        adapter = DeepSeekHarnessAdapter(self.config())
        self.assertEqual(adapter.compatibility(("tools",), contract_version="9.0").status, "incompatible")
        result = adapter.compatibility(("execute_code",))
        self.assertEqual(result.status, "incompatible")
        self.assertEqual(result.reason, "unknown_required_capability")

    def test_remote_requires_auth_and_public_metadata_has_no_secret_value(self):
        config = self.config(base_url="https://deepseek.example.test", deployment="remote", auth_mode="bearer_ref", credential_ref="DEEPSEEK_TOKEN")
        metadata = config.public_metadata()
        self.assertEqual(metadata["deployment"], "remote")
        self.assertEqual(metadata["credential_ref"], "DEEPSEEK_TOKEN")
        self.assertNotIn("secret-value", repr(metadata))
        self.assertEqual(config.bridge_candidate().kind, "deepseek_harness")
        with self.assertRaises(DeepSeekHarnessError):
            self.config(base_url="https://deepseek.example.test", deployment="remote", auth_mode="none")

    def test_pinned_plugin_and_bridge_versions_are_required(self):
        with self.assertRaises(DeepSeekHarnessError):
            self.config(pinned_version="latest")
        with self.assertRaises(DeepSeekHarnessError):
            self.config(plugin_version="head")
        with self.assertRaises(DeepSeekHarnessError):
            self.config(plugin_capabilities={"unsafe": ("filesystem",)})

    def test_disabled_adapter_is_unavailable(self):
        adapter = DeepSeekHarnessAdapter(self.config(enabled=False))
        result = adapter.compatibility(("tools",))
        self.assertEqual(adapter.status(), "unavailable")
        self.assertEqual(result.status, "unavailable")
        self.assertEqual(result.reason, "adapter_disabled")


if __name__ == "__main__":
    unittest.main()

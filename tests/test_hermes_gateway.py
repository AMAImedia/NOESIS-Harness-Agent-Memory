import unittest

from noesis_harness.hermes_gateway import HermesGatewayAdapter, HermesGatewayConfig, HermesGatewayError


class HermesGatewayTests(unittest.TestCase):
    def test_local_gateway_is_loopback_and_version_pinned(self):
        config = HermesGatewayConfig("hermes-local", "http://127.0.0.1:8765", "2026.08.17", tool_scopes=("health.read", "models.read", "chat"))
        adapter = HermesGatewayAdapter(config)
        self.assertEqual(adapter.status(), "ready")
        self.assertTrue(adapter.capability_metadata()["tools"] is False)
        candidate = config.bridge_candidate()
        self.assertEqual(candidate.kind, "hermes_webui")
        self.assertEqual(candidate.base_url, "http://127.0.0.1:8765")

    def test_remote_requires_auth_and_keeps_secret_as_reference_only(self):
        config = HermesGatewayConfig("hermes-remote", "https://gateway.example.test", "2026.08.17", deployment="remote", auth_mode="bearer_ref", credential_ref="HERMES_TOKEN", tool_scopes=("health.read", "models.read", "chat", "tools.invoke"))
        metadata = config.public_metadata()
        self.assertEqual(metadata["auth_mode"], "bearer_ref")
        self.assertEqual(metadata["credential_ref"], "HERMES_TOKEN")
        self.assertNotIn("token-value", repr(metadata))
        self.assertTrue(HermesGatewayAdapter(config).capability_metadata()["tools"])

    def test_invalid_local_remote_version_and_scopes_fail_closed(self):
        with self.assertRaises(HermesGatewayError):
            HermesGatewayConfig("x", "https://gateway.example.test", "latest")
        with self.assertRaises(HermesGatewayError):
            HermesGatewayConfig("x", "https://gateway.example.test", "2026.08.17")
        with self.assertRaises(HermesGatewayError):
            HermesGatewayConfig("x", "https://gateway.example.test", "2026.08.17", deployment="remote", auth_mode="none")
        with self.assertRaises(HermesGatewayError):
            HermesGatewayConfig("x", "http://127.0.0.1:8765", "2026.08.17", tool_scopes=("filesystem.write",))
        with self.assertRaises(HermesGatewayError):
            HermesGatewayConfig("x", "http://127.0.0.1:8765", "2026.08.17", auth_mode="bearer_ref", credential_ref="not-a-valid-ref")

    def test_disabled_gateway_is_fail_soft(self):
        config = HermesGatewayConfig("hermes-disabled", "http://localhost:8765", "2026.08.17", enabled=False)
        self.assertEqual(HermesGatewayAdapter(config).status(), "unavailable")


if __name__ == "__main__":
    unittest.main()

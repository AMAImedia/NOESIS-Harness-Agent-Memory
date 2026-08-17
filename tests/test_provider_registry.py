import json
import unittest
import urllib.error
import urllib.request

from noesis_harness.health_server import HealthServer
from noesis_harness.provider_registry import CAPABILITY_KEYS, ModelDescriptor, ProviderDescriptor, ProviderRegistry, ProviderRegistryError, SUPPORTED_PROVIDER_KINDS, adapter_spec


FIXTURES = (
    ("ollama", "ollama-local", "llama3.1:8b", "ollama"),
    ("lm_studio", "lmstudio-local", "qwen2.5-7b", "openai-compatible"),
    ("llama_cpp", "llama-cpp-local", "model.gguf", "openai-compatible"),
    ("vllm", "vllm-local", "deepseek-coder", "openai-compatible"),
    ("openai_compatible", "gateway-local", "local-model", "openai-compatible"),
)


def registry_fixture():
    return ProviderRegistry(tuple(
        ProviderDescriptor(
            provider_id=provider_id,
            kind=kind,
            status="ready",
            endpoint_kind=endpoint_kind,
            models=(ModelDescriptor(model_id=model_id, provider=kind, endpoint_kind=endpoint_kind, capabilities={"tools": True, "vision": False, "structured_output": True}),),
        )
        for kind, provider_id, model_id, endpoint_kind in FIXTURES
    ))


class ProviderRegistryTests(unittest.TestCase):
    def test_all_provider_fixtures_are_declarative_and_sorted(self):
        registry = registry_fixture()
        envelope = registry.envelope()
        self.assertTrue(envelope.ok)
        self.assertEqual(envelope.status, "ready")
        self.assertEqual(len(envelope.data["models"]), 5)
        self.assertEqual([item["provider"] for item in envelope.data["models"]], sorted(item["provider"] for item in envelope.data["models"]))
        self.assertNotIn("api_key", envelope.to_json())

    def test_empty_registry_is_unavailable_not_fake_ready(self):
        envelope = ProviderRegistry().envelope()
        self.assertTrue(envelope.ok)
        self.assertEqual(envelope.status, "unavailable")
        self.assertEqual(envelope.data["models"], [])
        self.assertIn("no_verified_provider_models", envelope.unavailable_reasons)

    def test_provider_validation_is_fail_closed(self):
        with self.assertRaises(ProviderRegistryError):
            ProviderDescriptor(provider_id="x", kind="unknown")
        with self.assertRaises(ProviderRegistryError):
            ProviderRegistry((ProviderDescriptor(provider_id="x", kind="ollama"), ProviderDescriptor(provider_id="x", kind="ollama")))
        with self.assertRaises(ProviderRegistryError):
            ProviderRegistry.validate_public_metadata({"api_key": "secret"})

    def test_adapter_specs_are_static_and_capability_complete(self):
        for kind in SUPPORTED_PROVIDER_KINDS:
            spec = adapter_spec(kind)
            self.assertEqual(spec.kind, kind)
            self.assertTrue(spec.health_path.startswith("/"))
            self.assertTrue(spec.models_path.startswith("/"))
            self.assertEqual(set(spec.default_capabilities), set(CAPABILITY_KEYS))
            self.assertNotIn("token", repr(spec).lower())
            self.assertNotIn("secret", repr(spec).lower())

    def test_unknown_capability_is_rejected(self):
        with self.assertRaises(ProviderRegistryError):
            ModelDescriptor(model_id="x", provider="ollama", capabilities={"execute_code": True}).to_record()

    def test_partial_provider_status_is_degraded(self):
        registry = ProviderRegistry((ProviderDescriptor(provider_id="hermes", kind="hermes_webui", status="unavailable"),))
        envelope = registry.envelope()
        self.assertEqual(envelope.status, "unavailable")
        self.assertEqual(envelope.data["models"], [])


class ModelsEndpointTests(unittest.TestCase):
    def _get(self, url):
        with urllib.request.urlopen(url, timeout=2) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def test_models_endpoint_returns_metadata_only(self):
        with HealthServer(port=0, provider_registry=registry_fixture()) as server:
            code, payload = self._get(f"http://{server.address[0]}:{server.address[1]}/models")
            self.assertEqual(code, 200)
            self.assertEqual(payload["status"], "ready")
            self.assertEqual(len(payload["data"]["models"]), 5)
            self.assertNotIn("api_key", json.dumps(payload))
            self.assertNotIn("authorization", json.dumps(payload).lower())

    def test_models_endpoint_default_is_explicitly_unavailable(self):
        with HealthServer(port=0) as server:
            code, payload = self._get(f"http://{server.address[0]}:{server.address[1]}/models")
            self.assertEqual(code, 200)
            self.assertEqual(payload["status"], "unavailable")
            self.assertEqual(payload["data"]["models"], [])


if __name__ == "__main__":
    unittest.main()

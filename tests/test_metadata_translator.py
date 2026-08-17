import unittest

from noesis_harness.metadata_translator import MetadataTranslationError, translate_metadata


class MetadataTranslatorTests(unittest.TestCase):
    def test_translates_hermes_metadata_without_execution(self):
        result = translate_metadata("hermes_webui", {"id": "hermes-local", "endpoint": "http://127.0.0.1:8765", "version": "2026.08.17", "tool_scopes": ["health.read", "models.read"], "ui_hint": "dark"})
        self.assertEqual(result.status, "translated")
        self.assertEqual(result.metadata["provider"], "hermes_webui")
        self.assertEqual(result.metadata["host"], "127.0.0.1")
        self.assertEqual(result.dropped_fields, ("ui_hint",))

    def test_translates_deepseek_plugin_capabilities(self):
        result = translate_metadata("deepseek_harness", {"id": "dsh-local", "base_url": "http://localhost:9000", "pinned_version": "2026.08.17", "plugin_id": "memory", "plugin_version": "1.0.0", "plugin_capabilities": {"memory": ["long_context"]}})
        self.assertEqual(result.status, "translated")
        self.assertEqual(result.metadata["provider"], "deepseek_harness")
        self.assertEqual(result.metadata["plugin_capabilities"], {"memory": ["long_context"]})

    def test_execution_presets_and_secrets_are_rejected(self):
        for payload in ({"command": "run"}, {"preset": {"steps": []}}, {"api_key": "value"}, {"system_prompt": "do this"}):
            with self.assertRaises(MetadataTranslationError):
                translate_metadata("hermes_webui", dict({"id": "x", "base_url": "http://127.0.0.1:1", "version": "1.0.0"}, **payload))

    def test_unsafe_scope_or_remote_without_auth_fails_through_adapter_validation(self):
        with self.assertRaises(ValueError):
            translate_metadata("hermes_webui", {"id": "x", "base_url": "http://127.0.0.1:1", "version": "1.0.0", "tool_scopes": ["shell.exec"]})
        with self.assertRaises(ValueError):
            translate_metadata("deepseek_harness", {"id": "x", "base_url": "https://example.test", "version": "1.0.0"})

    def test_unknown_source_is_rejected(self):
        with self.assertRaises(MetadataTranslationError):
            translate_metadata("foreign_preset", {})


if __name__ == "__main__":
    unittest.main()

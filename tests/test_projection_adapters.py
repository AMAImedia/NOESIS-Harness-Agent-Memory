import json
import unittest

from noesis_harness.projection_adapters import (
    AdapterRegistry,
    Consumer,
    Finding,
    JsonAdapter,
    MarkdownAdapter,
    TomlAdapter,
    canonical_digest,
    default_registry,
    emit_all,
    slugify,
)


class _EchoAdapter(Consumer):
    def __init__(self, adapter_name):
        self._name = adapter_name

    def name(self):
        return self._name

    def emit(self, record):
        return {"filename": self._name, "content": str(record.get("name", ""))}


def sample_record():
    return {
        "name": "Hello World",
        "title": "Hello World",
        "body": "A short body.",
        "tags": ["a", "b"],
        "count": 3,
    }


class ProjectionAdaptersTests(unittest.TestCase):
    def test_register_and_names_sorted(self):
        registry = AdapterRegistry()
        registry.register(_EchoAdapter("zeta"))
        registry.register(_EchoAdapter("alpha"))
        registry.register(_EchoAdapter("mid"))
        self.assertEqual(registry.names(), ["alpha", "mid", "zeta"])

    def test_duplicate_register_raises_value_error(self):
        registry = AdapterRegistry()
        registry.register(MarkdownAdapter())
        with self.assertRaises(ValueError):
            registry.register(MarkdownAdapter())

    def test_get_returns_adapter_and_unknown_raises(self):
        registry = default_registry()
        self.assertIsInstance(registry.get("markdown"), MarkdownAdapter)
        with self.assertRaises(KeyError):
            registry.get("does-not-exist")

    def test_emit_single_consumer(self):
        registry = default_registry()
        artifacts = registry.emit(sample_record(), ["json"])
        self.assertEqual(list(artifacts), ["json"])
        self.assertEqual(artifacts["json"]["consumer"], "json")

    def test_emit_multiple_consumers(self):
        registry = default_registry()
        artifacts = registry.emit(sample_record(), ["toml", "markdown"])
        self.assertEqual(sorted(artifacts), ["markdown", "toml"])
        self.assertEqual(artifacts["markdown"]["consumer"], "markdown")
        self.assertEqual(artifacts["toml"]["consumer"], "toml")

    def test_emit_unknown_consumer_raises_key_error(self):
        registry = default_registry()
        with self.assertRaises(KeyError):
            registry.emit(sample_record(), ["nope"])

    def test_render_stamps_consumer_and_source_digest(self):
        record = sample_record()
        artifact = MarkdownAdapter().render(record)
        self.assertEqual(artifact["consumer"], "markdown")
        self.assertEqual(artifact["source_digest"], canonical_digest(record))

    def test_source_digest_stable_across_dict_key_order(self):
        first = {"a": 1, "b": [2, 3], "c": {"d": 4}}
        second = {"c": {"d": 4}, "b": [2, 3], "a": 1}
        self.assertEqual(canonical_digest(first), canonical_digest(second))
        self.assertTrue(canonical_digest(first).startswith("sha256:"))
        self.assertEqual(len(canonical_digest(first)), len("sha256:") + 64)

    def test_markdown_filename_and_slug(self):
        artifact = MarkdownAdapter().emit({"name": "Hello World", "body": "x"})
        self.assertEqual(artifact["filename"], "hello-world.md")
        self.assertIn("title:", artifact["content"])
        self.assertTrue(artifact["content"].startswith("---\n"))
        self.assertTrue(artifact["content"].endswith("x"))

    def test_json_content_parses_back(self):
        record = sample_record()
        artifact = JsonAdapter().emit(record)
        self.assertEqual(artifact["filename"], "hello-world.json")
        self.assertEqual(json.loads(artifact["content"]), record)

    def test_toml_content_has_title_and_list_lines(self):
        record = sample_record()
        artifact = TomlAdapter().emit(record)
        self.assertEqual(artifact["filename"], "hello-world.toml")
        self.assertIn('title = "Hello World"', artifact["content"])
        self.assertIn('tags = ["a", "b"]', artifact["content"])
        self.assertIn("count = 3", artifact["content"])

    def test_toml_skips_nested_dict_and_none(self):
        artifact = TomlAdapter().emit(
            {"name": "n", "nested": {"x": 1}, "nothing": None, "ok": "v"}
        )
        content = artifact["content"]
        self.assertNotIn("nested", content)
        self.assertNotIn("nothing", content)
        self.assertIn('ok = "v"', content)

    def test_slugify_edge_cases(self):
        self.assertEqual(slugify("Hello, World!"), "hello-world")
        self.assertEqual(slugify("  Foo__Bar  "), "foo-bar")
        self.assertEqual(slugify("A---B"), "a-b")
        self.assertEqual(slugify(""), "untitled")
        self.assertEqual(slugify("***"), "untitled")
        self.assertEqual(slugify("Already-low"), "already-low")

    def test_validate_missing_filename_is_error_with_remediation(self):
        registry = default_registry()
        findings = registry.validate({"markdown": {"content": "x"}})
        errors = [f for f in findings if f.severity == "error"]
        self.assertTrue(errors)
        self.assertTrue(all(f.remediation for f in errors))
        self.assertTrue(any("filename" in f.message for f in errors))

    def test_validate_empty_on_good_artifacts(self):
        registry = default_registry()
        artifacts = registry.emit(sample_record())
        self.assertEqual(registry.validate(artifacts), [])

    def test_validate_flags_unknown_consumer(self):
        registry = default_registry()
        findings = registry.validate({"ghost": {"filename": "x", "content": "y"}})
        self.assertTrue(findings)
        self.assertEqual(findings[0].severity, "error")
        self.assertEqual(findings[0].consumer, "ghost")
        self.assertTrue(findings[0].remediation)

    def test_default_registry_has_three_adapters(self):
        registry = default_registry()
        self.assertEqual(registry.names(), ["json", "markdown", "toml"])
        self.assertIsInstance(registry.get("json"), JsonAdapter)
        self.assertIsInstance(registry.get("toml"), TomlAdapter)

    def test_determinism_across_runs(self):
        registry = default_registry()
        record = sample_record()
        first = registry.emit(record)
        second = registry.emit(record)
        self.assertEqual(first, second)
        self.assertEqual(sorted(first), ["json", "markdown", "toml"])

    def test_emit_all_matches_registry_emit(self):
        registry = default_registry()
        record = sample_record()
        self.assertEqual(
            emit_all(record, registry, ["json"]),
            registry.emit(record, ["json"]),
        )

    def test_finding_rejects_invalid_severity_and_empty_remediation(self):
        with self.assertRaises(ValueError):
            Finding(severity="fatal", consumer="x", message="m", remediation="r")
        with self.assertRaises(ValueError):
            Finding(severity="error", consumer="x", message="m", remediation="")

    def test_consumer_is_abstract(self):
        with self.assertRaises(TypeError):
            Consumer()


if __name__ == "__main__":
    unittest.main()

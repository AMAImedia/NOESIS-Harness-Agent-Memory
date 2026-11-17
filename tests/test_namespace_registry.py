"""tests/test_namespace_registry.py

Unit tests for noesis_harness.namespace_registry.

Stdlib only. Run: python -m unittest tests.test_namespace_registry -q
"""

import re
import unittest

from noesis_harness.namespace_registry import (
    ALLOWED_RE,
    MAX_NAME_LEN,
    SEPARATOR,
    NamespaceError,
    NamespaceRegistry,
    qualified,
    sanitize,
)


class TestSanitize(unittest.TestCase):
    def test_lowercases_and_replaces_disallowed(self):
        self.assertEqual(sanitize("Hello, World!"), "hello-world")

    def test_collapses_and_strips_separators(self):
        self.assertEqual(sanitize("  --Foo__Bar!!  "), "foo-bar")

    def test_empty_and_only_separators_become_unnamed(self):
        self.assertEqual(sanitize(""), "unnamed")
        self.assertEqual(sanitize("   "), "unnamed")
        self.assertEqual(sanitize("..."), "unnamed")
        self.assertEqual(sanitize("___---"), "unnamed")

    def test_single_separators_are_preserved_inside(self):
        self.assertEqual(sanitize("foo_bar"), "foo_bar")
        self.assertEqual(sanitize("Foo.Bar"), "foo.bar")
        self.assertEqual(sanitize("a-b"), "a-b")

    def test_runs_never_produce_double_underscore(self):
        for raw in ("foo__bar", "foo._bar", "foo-.bar", "foo__BAR"):
            self.assertNotIn(SEPARATOR, sanitize(raw))

    def test_unicode_and_leading_punctuation(self):
        self.assertEqual(sanitize("café"), "caf")
        self.assertEqual(sanitize(".hidden"), "hidden")
        self.assertEqual(sanitize("123abc"), "123abc")

    def test_non_string_raises(self):
        with self.assertRaises(NamespaceError):
            sanitize(None)  # type: ignore[arg-type]
        with self.assertRaises(NamespaceError):
            sanitize(123)  # type: ignore[arg-type]


class TestQualified(unittest.TestCase):
    def test_format(self):
        self.assertEqual(qualified("Acme", "Reviewer"), "acme__reviewer")
        self.assertEqual(qualified("My Plugin", "build step"), "my-plugin__build-step")

    def test_result_matches_allowed_re_and_has_one_separator(self):
        result = qualified("Acme", "reviewer")
        self.assertIsNotNone(re.match(ALLOWED_RE, result))
        self.assertEqual(result.count(SEPARATOR), 1)

    def test_truncation_keeps_namespace_and_separator(self):
        namespace = "n" * 40
        name = "m" * 40
        result = qualified(namespace, name)
        self.assertEqual(len(result), MAX_NAME_LEN)
        self.assertTrue(result.startswith(namespace + SEPARATOR))
        self.assertEqual(result, namespace + SEPARATOR + ("m" * 22))
        self.assertIsNotNone(re.match(ALLOWED_RE, result))

    def test_truncation_with_overlong_namespace(self):
        result = qualified("n" * 70, "x")
        self.assertEqual(len(result), MAX_NAME_LEN)
        self.assertIn(SEPARATOR, result)
        self.assertEqual(result, ("n" * 61) + SEPARATOR + "x")
        self.assertIsNotNone(re.match(ALLOWED_RE, result))

    def test_short_inputs_are_untouched(self):
        self.assertEqual(qualified("a", "b"), "a__b")


class TestNamespaceRegistry(unittest.TestCase):
    def test_register_returns_qualified_id(self):
        registry = NamespaceRegistry()
        self.assertEqual(registry.register("Acme", "Reviewer"), "acme__reviewer")

    def test_register_same_pair_is_idempotent(self):
        registry = NamespaceRegistry()
        first = registry.register("acme", "reviewer")
        second = registry.register("acme", "reviewer")
        self.assertEqual(first, second)
        self.assertEqual(registry.ids(), ["acme__reviewer"])

    def test_register_conflicting_pair_raises(self):
        registry = NamespaceRegistry()
        registry.register("acme", "foo")
        with self.assertRaises(NamespaceError):
            registry.register("acme", "foo!")

    def test_register_conflicting_namespace_raises(self):
        registry = NamespaceRegistry()
        registry.register("My Plugin", "x")
        with self.assertRaises(NamespaceError):
            registry.register("my-plugin", "x")

    def test_resolve_and_get(self):
        registry = NamespaceRegistry()
        registry.register("Acme", "Reviewer")
        self.assertEqual(registry.resolve("acme__reviewer"), ("Acme", "Reviewer"))
        entry = registry.get("acme__reviewer")
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry["id"], "acme__reviewer")
        self.assertEqual(entry["namespace"], "Acme")
        self.assertEqual(entry["name"], "Reviewer")
        self.assertEqual(entry["bare"], "reviewer")

    def test_get_returns_defensive_copy(self):
        registry = NamespaceRegistry()
        registry.register("acme", "reviewer")
        entry = registry.get("acme__reviewer")
        assert entry is not None
        entry["name"] = "mutated"
        self.assertEqual(registry.get("acme__reviewer")["name"], "reviewer")

    def test_resolve_unknown_wellformed_returns_none(self):
        registry = NamespaceRegistry()
        self.assertIsNone(registry.resolve("missing__thing"))
        self.assertIsNone(registry.get("missing__thing"))

    def test_resolve_invalid_raises_namespace_error(self):
        registry = NamespaceRegistry()
        for bad in ("", "Bad Id", "no-separator", "UPPER__case", None, 42):
            with self.assertRaises(NamespaceError):
                registry.resolve(bad)
            with self.assertRaises(NamespaceError):
                registry.get(bad)

    def test_bare_names_sorted_unique(self):
        registry = NamespaceRegistry()
        registry.register("acme", "reviewer")
        registry.register("beta", "reviewer")
        registry.register("acme", "build")
        self.assertEqual(registry.bare_names(), ["build", "reviewer"])

    def test_collisions_detection(self):
        registry = NamespaceRegistry()
        registry.register("acme", "reviewer")
        registry.register("beta", "reviewer")
        registry.register("acme", "build")
        self.assertEqual(
            registry.collisions(),
            {"reviewer": ["acme__reviewer", "beta__reviewer"]},
        )

    def test_no_collisions_when_names_unique(self):
        registry = NamespaceRegistry()
        registry.register("acme", "reviewer")
        registry.register("acme", "build")
        self.assertEqual(registry.collisions(), {})

    def test_disambiguate_sorted(self):
        registry = NamespaceRegistry()
        registry.register("beta", "reviewer")
        registry.register("acme", "reviewer")
        self.assertEqual(
            registry.disambiguate("reviewer"),
            ["acme__reviewer", "beta__reviewer"],
        )
        self.assertEqual(registry.disambiguate("Reviewer"), [
            "acme__reviewer",
            "beta__reviewer",
        ])
        self.assertEqual(registry.disambiguate("nope"), [])

    def test_ids_sorted(self):
        registry = NamespaceRegistry()
        registry.register("beta", "z")
        registry.register("acme", "a")
        registry.register("acme", "m")
        self.assertEqual(
            registry.ids(), ["acme__a", "acme__m", "beta__z"]
        )

    def test_json_roundtrip_preserves_entries(self):
        registry = NamespaceRegistry()
        registry.register("Acme", "Reviewer")
        registry.register("beta", "reviewer")
        registry.register("acme", "build")
        restored = NamespaceRegistry.from_json(registry.to_json())
        self.assertEqual(restored.ids(), registry.ids())
        self.assertEqual(restored.bare_names(), registry.bare_names())
        self.assertEqual(restored.collisions(), registry.collisions())
        self.assertEqual(
            restored.resolve("acme__reviewer"), registry.resolve("acme__reviewer")
        )
        self.assertEqual(restored.to_json(), registry.to_json())

    def test_empty_registry(self):
        registry = NamespaceRegistry()
        self.assertEqual(registry.ids(), [])
        self.assertEqual(registry.bare_names(), [])
        self.assertEqual(registry.collisions(), {})
        self.assertIsNone(registry.resolve("a__b"))
        self.assertEqual(
            registry.to_json(), '{"entries":[],"version":1}'
        )
        restored = NamespaceRegistry.from_json(registry.to_json())
        self.assertEqual(restored.ids(), [])

    def test_determinism_across_registration_order(self):
        first = NamespaceRegistry()
        first.register("beta", "reviewer")
        first.register("acme", "build")
        first.register("acme", "reviewer")
        second = NamespaceRegistry()
        second.register("acme", "reviewer")
        second.register("acme", "build")
        second.register("beta", "reviewer")
        self.assertEqual(first.to_json(), second.to_json())
        self.assertEqual(first.ids(), second.ids())
        self.assertEqual(first.collisions(), second.collisions())

    def test_from_json_rejects_bad_payloads(self):
        with self.assertRaises(NamespaceError):
            NamespaceRegistry.from_json("not json")
        with self.assertRaises(NamespaceError):
            NamespaceRegistry.from_json('{"version":2,"entries":[]}')
        with self.assertRaises(NamespaceError):
            NamespaceRegistry.from_json(
                '{"version":1,"entries":[{"id":"wrong__id",'
                '"namespace":"acme","name":"reviewer"}]}'
            )
        with self.assertRaises(NamespaceError):
            NamespaceRegistry.from_json(None)  # type: ignore[arg-type]

    def test_constants_and_error_type(self):
        self.assertEqual(SEPARATOR, "__")
        self.assertEqual(MAX_NAME_LEN, 64)
        self.assertEqual(ALLOWED_RE, r"^[a-z0-9][a-z0-9._-]*$")
        self.assertTrue(issubclass(NamespaceError, ValueError))


if __name__ == "__main__":
    unittest.main()

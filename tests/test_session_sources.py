import unittest
import uuid

from noesis_harness.session_sources import (
    FileKind,
    HarnessSpec,
    REGISTRY,
    SessionSourceRegistry,
    kind_for_path,
    register_harness,
)


def make_kind(name, suffix, appendable=False, marker=None):
    calls = []

    def match(path, suffix=suffix):
        return path.endswith(suffix)

    def parse(path, name=name, marker=marker, calls=calls):
        calls.append(("parse", path))
        payload = {"name": name, "path": path}
        if marker is not None:
            payload[marker[0]] = marker[1]
        return payload

    kind = FileKind(name=name, match=match, parse=parse)

    if appendable:

        def parse_from(path, offset, name=name, calls=calls):
            calls.append(("parse_from", path, offset))
            return {"name": name, "path": path, "offset": offset}

        kind = FileKind(name=name, match=match, parse=parse, parse_from=parse_from)

    return kind, calls


def make_spec(name, files, kinds):
    return HarnessSpec(name=name, files=lambda files=tuple(files): list(files), kinds=list(kinds))


class SessionSourceRegistryTests(unittest.TestCase):
    def test_register_and_harnesses_sorted(self):
        registry = SessionSourceRegistry()
        registry.register(make_spec("zeta", [], []))
        registry.register(make_spec("alpha", [], []))
        self.assertEqual(registry.harnesses(), ["alpha", "zeta"])

    def test_duplicate_harness_name_raises(self):
        registry = SessionSourceRegistry()
        registry.register(make_spec("dup", [], []))
        with self.assertRaises(ValueError):
            registry.register(make_spec("dup", [], []))

    def test_kind_for_path_match(self):
        kind, _ = make_kind("jsonl", ".jsonl")
        registry = SessionSourceRegistry()
        registry.register(make_spec("harness-a", ["a.jsonl"], [kind]))
        self.assertEqual(registry.kind_for_path("a.jsonl"), ("harness-a", "jsonl"))

    def test_kind_for_path_no_match(self):
        kind, _ = make_kind("jsonl", ".jsonl")
        registry = SessionSourceRegistry()
        registry.register(make_spec("harness-a", ["a.jsonl"], [kind]))
        self.assertIsNone(registry.kind_for_path("a.log"))

    def test_kind_for_path_first_harness_in_sorted_order(self):
        shared_a, _ = make_kind("shared", ".jsonl")
        shared_z, _ = make_kind("shared", ".jsonl")
        registry = SessionSourceRegistry()
        registry.register(make_spec("zeta", ["x.jsonl"], [shared_z]))
        registry.register(make_spec("alpha", ["x.jsonl"], [shared_a]))
        self.assertEqual(registry.kind_for_path("x.jsonl"), ("alpha", "shared"))

    def test_discover_ordering_deterministic(self):
        kind, _ = make_kind("jsonl", ".jsonl")
        registry = SessionSourceRegistry()
        registry.register(make_spec("zeta", ["b.jsonl", "a.jsonl"], [kind]))
        registry.register(make_spec("alpha", ["z.jsonl", "m.jsonl"], [kind]))
        self.assertEqual(
            registry.discover(),
            [
                ("alpha", "jsonl", "m.jsonl"),
                ("alpha", "jsonl", "z.jsonl"),
                ("zeta", "jsonl", "a.jsonl"),
                ("zeta", "jsonl", "b.jsonl"),
            ],
        )

    def test_discover_skips_unmatched_and_dedupes(self):
        kind, _ = make_kind("jsonl", ".jsonl")
        registry = SessionSourceRegistry()
        registry.register(make_spec("harness-a", ["a.jsonl", "a.jsonl", "skip.log"], [kind]))
        self.assertEqual(registry.discover(), [("harness-a", "jsonl", "a.jsonl")])

    def test_parse_path_stamps_harness_and_kind(self):
        kind, _ = make_kind("jsonl", ".jsonl")
        registry = SessionSourceRegistry()
        registry.register(make_spec("harness-a", ["a.jsonl"], [kind]))
        parsed = registry.parse_path("a.jsonl")
        self.assertEqual(parsed["harness"], "harness-a")
        self.assertEqual(parsed["kind"], "jsonl")
        self.assertEqual(parsed["path"], "a.jsonl")

    def test_parse_path_preserves_existing_stamp(self):
        kind, _ = make_kind("jsonl", ".jsonl", marker=("harness", "already"))
        registry = SessionSourceRegistry()
        registry.register(make_spec("harness-a", ["a.jsonl"], [kind]))
        parsed = registry.parse_path("a.jsonl")
        self.assertEqual(parsed["harness"], "already")
        self.assertEqual(parsed["kind"], "jsonl")

    def test_parse_path_unknown_raises_keyerror(self):
        registry = SessionSourceRegistry()
        with self.assertRaises(KeyError):
            registry.parse_path("missing.jsonl")

    def test_parse_appended_uses_parse_from(self):
        kind, calls = make_kind("jsonl", ".jsonl", appendable=True)
        registry = SessionSourceRegistry()
        registry.register(make_spec("harness-a", ["a.jsonl"], [kind]))
        appended = registry.parse_appended("a.jsonl")
        self.assertEqual(appended["offset"], 0)
        self.assertIn(("parse_from", "a.jsonl", 0), calls)

    def test_parse_appended_without_incremental_raises_valueerror(self):
        kind, _ = make_kind("jsonl", ".jsonl")
        registry = SessionSourceRegistry()
        registry.register(make_spec("harness-a", ["a.jsonl"], [kind]))
        with self.assertRaises(ValueError):
            registry.parse_appended("a.jsonl")

    def test_appendable_kinds_correct(self):
        cold, _ = make_kind("cold", ".cold")
        hot, _ = make_kind("hot", ".hot", appendable=True)
        registry = SessionSourceRegistry()
        registry.register(make_spec("zeta", [], [cold]))
        registry.register(make_spec("alpha", [], [hot, cold]))
        self.assertEqual(registry.appendable_kinds(), [("alpha", "hot")])

    def test_empty_registry_behavior(self):
        registry = SessionSourceRegistry()
        self.assertEqual(registry.harnesses(), [])
        self.assertEqual(registry.discover(), [])
        self.assertIsNone(registry.kind_for_path("anything"))
        self.assertEqual(registry.appendable_kinds(), [])

    def test_module_level_registry_thin_functions(self):
        self.assertIsInstance(REGISTRY, SessionSourceRegistry)
        name = "test-isolated-harness-%s" % uuid.uuid4().hex
        before = len(REGISTRY.harnesses())
        register_harness(make_spec(name, ["isolated-%s.jsonl" % name], [make_kind("jsonl", ".jsonl")[0]]))
        self.assertEqual(len(REGISTRY.harnesses()), before + 1)
        found = kind_for_path("isolated-%s.jsonl" % name)
        self.assertEqual(found, (name, "jsonl"))


if __name__ == "__main__":
    unittest.main()

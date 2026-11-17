"""tests/test_id_gen.py

Unit tests for noesis_harness.id_gen.
"""

from __future__ import annotations

import re
import string
import unittest

from noesis_harness import id_gen


class TestContentId(unittest.TestCase):
    def test_determinism_same_input(self):
        a = id_gen.content_id("agent", "task", 1)
        b = id_gen.content_id("agent", "task", 1)
        self.assertEqual(a, b)

    def test_determinism_across_runs_format(self):
        val = id_gen.content_id("x", {"k": "v"})
        self.assertEqual(len(val), 64)
        self.assertTrue(re.fullmatch(r"[0-9a-f]{64}", val))

    def test_order_independence_scalars(self):
        self.assertEqual(
            id_gen.content_id("a", "b", "c"),
            id_gen.content_id("c", "a", "b"),
        )

    def test_order_independence_dicts(self):
        self.assertEqual(
            id_gen.content_id({"a": 1, "b": 2}),
            id_gen.content_id({"b": 2, "a": 1}),
        )

    def test_dict_key_order_irrelevant(self):
        self.assertEqual(
            id_gen.content_id("scope", {"x": 1, "y": 2}),
            id_gen.content_id("scope", {"y": 2, "x": 1}),
        )

    def test_different_content_different_id(self):
        self.assertNotEqual(
            id_gen.content_id("a", "b"),
            id_gen.content_id("a", "c"),
        )

    def test_empty_parts_stable(self):
        self.assertEqual(id_gen.content_id(), id_gen.content_id())

    def test_unicode_stable(self):
        a = id_gen.content_id("café", "日本語")
        b = id_gen.content_id("café", "日本語")
        self.assertEqual(a, b)

    def test_list_vs_scalar_distinct(self):
        self.assertNotEqual(
            id_gen.content_id(["a", "b"]),
            id_gen.content_id("a", "b"),
        )


class TestShortId(unittest.TestCase):
    def test_default_length(self):
        sid = id_gen.short_id(("agent", "task"))
        self.assertEqual(len(sid), 12)

    def test_custom_length(self):
        sid = id_gen.short_id(("agent", "task"), length=8)
        self.assertEqual(len(sid), 8)

    def test_length_clamped_min(self):
        self.assertEqual(len(id_gen.short_id("x", length=0)), 1)

    def test_length_clamped_max(self):
        self.assertEqual(len(id_gen.short_id("x", length=999)), 64)

    def test_prefix_of_content_id(self):
        full = id_gen.content_id("alpha", "beta")
        self.assertEqual(id_gen.short_id(("alpha", "beta"), length=16), full[:16])

    def test_determinism(self):
        self.assertEqual(
            id_gen.short_id(("p", 1)),
            id_gen.short_id(("p", 1)),
        )

    def test_uniqueness_over_many_inputs(self):
        inputs = [(f"scope{i}", f"key{i}") for i in range(5000)]
        sids = {id_gen.short_id(p, length=12) for p in inputs}
        self.assertEqual(len(sids), len(inputs))

    def test_hex_only(self):
        sid = id_gen.short_id(("z", "q"), length=20)
        self.assertTrue(set(sid).issubset(set(string.hexdigits.lower())))


class TestUuidSafe(unittest.TestCase):
    def test_format_32_hex(self):
        u = id_gen.uuid_safe()
        self.assertEqual(len(u), 32)
        self.assertTrue(re.fullmatch(r"[0-9a-f]{32}", u))

    def test_unique_across_many(self):
        us = {id_gen.uuid_safe() for _ in range(10000)}
        self.assertEqual(len(us), 10000)

    def test_not_equal_to_content_id(self):
        self.assertNotEqual(id_gen.uuid_safe(), id_gen.content_id("anything"))


if __name__ == "__main__":
    unittest.main()

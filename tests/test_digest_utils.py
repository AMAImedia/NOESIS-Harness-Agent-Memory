"""Tests for noesis_harness.digest_utils.

All helpers are pure and deterministic; these tests pin that contract.
"""

import unittest

from noesis_harness.digest_utils import (
    canonical_json,
    fingerprint,
    sha256_hex,
    stable_digest,
)


class TestCanonicalJson(unittest.TestCase):
    def test_round_trip_determinism(self):
        obj = {"b": 1, "a": 2, "c": [3, 4]}
        self.assertEqual(canonical_json(obj), canonical_json(dict(obj)))

    def test_sorted_keys(self):
        self.assertEqual(canonical_json({"b": 1, "a": 2}), '{"a":2,"b":1}')

    def test_compact_separators(self):
        self.assertEqual(canonical_json({"a": 1, "b": 2}), '{"a":1,"b":2}')

    def test_unicode_preserved(self):
        self.assertEqual(canonical_json({"name": "héllo—ω"}),
                         '{"name":"héllo—ω"}')


class TestSha256Hex(unittest.TestCase):
    def test_string_input(self):
        self.assertEqual(
            sha256_hex("abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        )

    def test_bytes_input(self):
        self.assertEqual(sha256_hex(b"abc"), sha256_hex("abc"))

    def test_empty_string(self):
        self.assertEqual(
            sha256_hex(""),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )


class TestFingerprint(unittest.TestCase):
    def test_order_independence_of_values(self):
        a = fingerprint("x", "y", {"k": 1, "j": 2})
        b = fingerprint("y", "x", {"j": 2, "k": 1})
        self.assertEqual(a, b)

    def test_different_parts_differ(self):
        self.assertNotEqual(fingerprint("x", "y"), fingerprint("x", "z"))

    def test_empty_parts(self):
        self.assertEqual(fingerprint(), sha256_hex(""))

    def test_binary_input_handling(self):
        self.assertEqual(fingerprint(b"abc"), fingerprint("abc"))

    def test_unicode_input(self):
        self.assertEqual(fingerprint("héllo—ω"),
                         fingerprint("héllo—ω".encode("utf-8")))
        self.assertEqual(fingerprint({"k": "héllo—ω"}),
                         fingerprint({"k": "héllo—ω"}))


class TestStableDigest(unittest.TestCase):
    def test_deterministic(self):
        obj = {"z": [1, 2], "a": "v", "m": {"n": True}}
        self.assertEqual(stable_digest(obj), stable_digest(dict(obj)))

    def test_order_independent(self):
        self.assertEqual(stable_digest({"a": 1, "b": 2}),
                         stable_digest({"b": 2, "a": 1}))

    def test_empty_object(self):
        self.assertEqual(stable_digest({}), sha256_hex("{}"))

    def test_distinct_objects_distinct(self):
        self.assertNotEqual(stable_digest({"a": 1}), stable_digest({"a": 2}))


if __name__ == "__main__":
    unittest.main()

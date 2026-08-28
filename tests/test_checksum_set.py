"""tests/test_checksum_set.py

Unit tests for noesis_harness/checksum_set.py — deterministic sha256 checksum set.

Asserts determinism, order-independent digest, stable empty digest, unicode
handling, idempotent (no double count) inserts, and sorted externalization.
Stdlib only.
"""

import hashlib
import unittest

from noesis_harness.checksum_set import ChecksumSet


class TestAddContains(unittest.TestCase):
    def test_add_then_contains(self):
        cs = ChecksumSet()
        cs.add("alpha")
        self.assertTrue(cs.contains("alpha"))

    def test_add_bytes_then_contains(self):
        cs = ChecksumSet()
        cs.add(b"alpha")
        self.assertTrue(cs.contains(b"alpha"))
        self.assertTrue(cs.contains("alpha"))

    def test_contains_missing(self):
        cs = ChecksumSet()
        cs.add("alpha")
        self.assertFalse(cs.contains("beta"))

    def test_str_and_bytes_same_digest(self):
        cs1 = ChecksumSet()
        cs1.add("hello")
        cs2 = ChecksumSet()
        cs2.add(b"hello")
        self.assertEqual(cs1.digest(), cs2.digest())
        self.assertEqual(cs1.to_list(), cs2.to_list())


class TestDigestDeterminism(unittest.TestCase):
    def test_digest_order_independence(self):
        a = ChecksumSet()
        a.add("one")
        a.add("two")
        a.add("three")
        b = ChecksumSet()
        b.add("three")
        b.add("one")
        b.add("two")
        self.assertEqual(a.digest(), b.digest())

    def test_digest_repeatable(self):
        cs = ChecksumSet()
        cs.add("x")
        cs.add("y")
        self.assertEqual(cs.digest(), cs.digest())

    def test_digest_matches_manual_fold(self):
        cs = ChecksumSet()
        items = ["a", "b", "c"]
        for it in items:
            cs.add(it)
        digests = sorted(hashlib.sha256(it.encode("utf-8")).hexdigest() for it in items)
        expected = hashlib.sha256("".join(digests).encode("ascii")).hexdigest()
        self.assertEqual(cs.digest(), expected)


class TestEmptyDigest(unittest.TestCase):
    def test_empty_digest_stable(self):
        cs = ChecksumSet()
        expected = hashlib.sha256("".encode("ascii")).hexdigest()
        self.assertEqual(cs.digest(), expected)
        self.assertEqual(cs.digest(), ChecksumSet().digest())

    def test_empty_to_list_empty(self):
        cs = ChecksumSet()
        self.assertEqual(cs.to_list(), [])
        self.assertEqual(len(cs), 0)


class TestUnicode(unittest.TestCase):
    def test_unicode_item(self):
        cs = ChecksumSet()
        cs.add("café — 日本語 — ελληνικά")
        self.assertTrue(cs.contains("café — 日本語 — ελληνικά"))

    def test_unicode_order_independence(self):
        a = ChecksumSet()
        a.add("α")
        a.add("β")
        b = ChecksumSet()
        b.add("β")
        b.add("α")
        self.assertEqual(a.digest(), b.digest())


class TestNoDoubleCount(unittest.TestCase):
    def test_repeat_add_idempotent(self):
        cs = ChecksumSet()
        self.assertTrue(cs.add("dup"))
        self.assertFalse(cs.add("dup"))
        self.assertFalse(cs.add("dup"))
        self.assertEqual(len(cs), 1)

    def test_to_list_has_no_duplicates(self):
        cs = ChecksumSet()
        for _ in range(5):
            cs.add("same")
        cs.add("other")
        self.assertEqual(cs.to_list(), sorted([
            hashlib.sha256(b"same").hexdigest(),
            hashlib.sha256(b"other").hexdigest(),
        ]))


class TestToListSorted(unittest.TestCase):
    def test_to_list_sorted(self):
        cs = ChecksumSet()
        cs.add("banana")
        cs.add("apple")
        cs.add("cherry")
        lst = cs.to_list()
        self.assertEqual(lst, sorted(lst))
        self.assertEqual(len(lst), 3)

    def test_to_list_reproducible_across_instances(self):
        a = ChecksumSet()
        b = ChecksumSet()
        for it in ["z", "m", "a", "q"]:
            a.add(it)
            b.add(it)
        self.assertEqual(a.to_list(), b.to_list())


if __name__ == "__main__":
    unittest.main()

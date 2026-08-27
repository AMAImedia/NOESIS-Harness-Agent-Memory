"""Tests for noesis_harness.watermark.

Covers determinism, order-independence, combine commutativity, empty, single,
unicode ids, and cross-version stability of the watermark digest.
"""

import unittest

from noesis_harness.watermark import watermark, combine


class TestWatermarkDeterminism(unittest.TestCase):
    def test_deterministic_same_input(self):
        ids = ["e1", "e2", "e3"]
        self.assertEqual(watermark(ids), watermark(ids))

    def test_deterministic_repeated_call(self):
        ids = ["a", "b"]
        first = watermark(ids)
        second = watermark(list(ids))
        self.assertEqual(first, second)

    def test_order_independence(self):
        ids = ["e3", "e1", "e2"]
        self.assertEqual(watermark(ids), watermark(["e1", "e2", "e3"]))

    def test_duplicate_ids_ignored(self):
        self.assertEqual(
            watermark(["e1", "e2", "e1"]),
            watermark(["e1", "e2"]),
        )


class TestWatermarkCombine(unittest.TestCase):
    def test_combine_commutativity(self):
        w1 = watermark(["a", "b"])
        w2 = watermark(["c", "d"])
        self.assertEqual(combine(w1, w2), combine(w2, w1))

    def test_combine_deterministic(self):
        w1 = watermark(["a"])
        w2 = watermark(["b"])
        self.assertEqual(combine(w1, w2), combine(w1, w2))

    def test_combine_with_empty(self):
        w = watermark(["x", "y"])
        empty = watermark([])
        self.assertEqual(combine(w, empty), w)


class TestWatermarkEdgeCases(unittest.TestCase):
    def test_empty_set(self):
        self.assertEqual(watermark([]), watermark([]))
        self.assertIsInstance(watermark([]), str)
        self.assertEqual(len(watermark([])), 64)

    def test_single_id(self):
        w = watermark(["only"])
        self.assertEqual(len(w), 64)
        self.assertEqual(w, watermark(["only"]))

    def test_unicode_ids(self):
        ids = ["évent-1", "事件-2", "संग्रह-3"]
        self.assertEqual(watermark(ids), watermark(list(reversed(ids))))

    def test_unicode_stable_digest(self):
        self.assertEqual(
            watermark(["日本語"]),
            "77710aedc74ecfa33685e33a6c7df5cc83004da1bdcef7fb280f5c2b2e97e0a5",
        )


class TestWatermarkStability(unittest.TestCase):
    def test_stable_digest_known_vector(self):
        # Fixed reference vectors; the encoding must keep these exact across
        # versions so watermarks stay comparable across coordinator upgrades.
        self.assertEqual(
            watermark([]),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )
        self.assertEqual(
            watermark(["alpha", "beta", "gamma"]),
            "f3220283d05d1ff2ae350cfe9e0e367cb5aef46e10efb203c8a53c678e2218c8",
        )
        self.assertEqual(
            watermark(["日本語"]),
            "77710aedc74ecfa33685e33a6c7df5cc83004da1bdcef7fb280f5c2b2e97e0a5",
        )

    def test_combine_produces_valid_digest(self):
        w = combine(watermark(["a"]), watermark(["b"]))
        self.assertEqual(len(w), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in w))


if __name__ == "__main__":
    unittest.main()

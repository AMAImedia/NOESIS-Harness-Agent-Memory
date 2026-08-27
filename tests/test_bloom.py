"""tests/test_bloom.py

Unit tests for noesis_harness/bloom.py — deterministic Bloom filter.

These tests assert determinism, no false negatives, bounded false positives, and
absence of any randomness or hidden state. Stdlib only.
"""

import math
import random
import unittest

from noesis_harness.bloom import Bloom


class TestBloomAddContains(unittest.TestCase):
    def test_add_then_contains(self):
        b = Bloom(1024, 5)
        b.add("alpha")
        self.assertTrue(b.might_contain("alpha"))

    def test_add_many_then_all_contain(self):
        b = Bloom(4096, 7)
        items = ["item-%d" % i for i in range(200)]
        for it in items:
            b.add(it)
        for it in items:
            self.assertTrue(b.might_contain(it))

    def test_add_bytes_item(self):
        b = Bloom(512, 4)
        b.add(b"raw-bytes")
        self.assertTrue(b.might_contain(b"raw-bytes"))

    def test_add_non_string_item(self):
        b = Bloom(512, 4)
        b.add(42)
        self.assertTrue(b.might_contain(42))


class TestBloomNotContains(unittest.TestCase):
    def test_fresh_filter_rejects(self):
        b = Bloom(1024, 5)
        self.assertFalse(b.might_contain("never-added"))

    def test_not_contains_after_adds(self):
        b = Bloom(2048, 6)
        for it in ["a", "b", "c", "d"]:
            b.add(it)
        # With a reasonably sized filter these are very unlikely to collide.
        self.assertFalse(b.might_contain("zzz-absent"))


class TestBloomNoFalseNegatives(unittest.TestCase):
    def test_large_insert_set_no_false_negatives(self):
        b = Bloom(8192, 8)
        items = ["k-%d" % i for i in range(1000)]
        for it in items:
            b.add(it)
        missed = [it for it in items if not b.might_contain(it)]
        self.assertEqual(missed, [])


class TestBloomDeterminism(unittest.TestCase):
    def test_same_inputs_same_result(self):
        def build():
            f = Bloom(1024, 5)
            for it in ["x", "y", "z", "w"]:
                f.add(it)
            return f

        a, b = build(), build()
        self.assertEqual(a._bits, b._bits)
        self.assertEqual(a.might_contain("x"), b.might_contain("x"))
        self.assertEqual(a.might_contain("absent"), b.might_contain("absent"))

    def test_deterministic_across_runs(self):
        # Positions are derived purely from item bytes + salt, not from RNG.
        f = Bloom(1024, 5)
        f.add("deterministic")
        g = Bloom(1024, 5)
        g.add("deterministic")
        self.assertEqual(f._bits, g._bits)

    def test_order_independent(self):
        items = ["p", "q", "r", "s", "t"]
        f1 = Bloom(2048, 6)
        for it in items:
            f1.add(it)
        f2 = Bloom(2048, 6)
        for it in reversed(items):
            f2.add(it)
        self.assertEqual(f1._bits, f2._bits)


class TestBloomIdempotency(unittest.TestCase):
    def test_re_add_is_noop(self):
        b = Bloom(1024, 5)
        first = b.add("dup")
        second = b.add("dup")
        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(b.count(), 1)
        self.assertTrue(b.might_contain("dup"))


class TestBloomFalsePositiveBehavior(unittest.TestCase):
    def test_false_positive_rate_within_bound(self):
        size = 10000
        hashes = 7
        inserted = 500
        b = Bloom(size, hashes)
        for i in range(inserted):
            b.add("x-%d" % i)
        # Probe many never-inserted items and measure observed rate.
        probe = ["absent-%d" % i for i in range(2000)]
        fp = sum(1 for p in probe if b.might_contain(p))
        observed = fp / len(probe)
        bound = b.false_positive_rate_estimate()
        # Observed rate should not exceed the theoretical bound by a wide margin.
        self.assertLessEqual(observed, bound + 0.05)

    def test_estimate_increases_with_inserts(self):
        b = Bloom(1000, 5)
        low = b.false_positive_rate_estimate(10)
        high = b.false_positive_rate_estimate(500)
        self.assertLess(low, high)

    def test_estimate_zero_for_empty(self):
        b = Bloom(1000, 5)
        self.assertEqual(b.false_positive_rate_estimate(), 0.0)

    def test_estimate_matches_formula(self):
        b = Bloom(1000, 5)
        n = 100
        m = 1000
        k = 5
        expected = (1.0 - math.exp(-k * n / m)) ** k
        self.assertAlmostEqual(b.false_positive_rate_estimate(n), expected, places=12)


class TestBloomSizeBound(unittest.TestCase):
    def test_bit_array_length_is_size(self):
        b = Bloom(777, 3)
        self.assertEqual(len(b._bits), 777)
        self.assertEqual(b.size(), 777)

    def test_positions_within_bounds(self):
        b = Bloom(256, 9)
        for pos in b._positions("anything"):
            self.assertTrue(0 <= pos < 256)

    def test_add_does_not_exceed_size_bits(self):
        b = Bloom(100, 4)
        for it in ["a", "b", "c", "d", "e"]:
            b.add(it)
        self.assertLessEqual(max(b._bits), 1)


class TestBloomNoRandomness(unittest.TestCase):
    def test_no_global_random_state_used(self):
        # Calling many adds/contain checks must not perturb random module state.
        before = random.getstate()
        b = Bloom(1024, 5)
        for i in range(100):
            b.add("r-%d" % i)
            b.might_contain("r-%d" % i)
        after = random.getstate()
        # getstate returns a tuple; the generator internal state is the 3rd elem.
        self.assertEqual(before[1], after[1])

    def test_constructor_rejects_nonpositive(self):
        with self.assertRaises(ValueError):
            Bloom(0, 3)
        with self.assertRaises(ValueError):
            Bloom(100, 0)
        with self.assertRaises(ValueError):
            Bloom(-5, 3)


if unittest.__name__:
    pass


if __name__ == "__main__":
    unittest.main()

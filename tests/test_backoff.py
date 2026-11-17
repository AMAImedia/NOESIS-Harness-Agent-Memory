"""Tests for noesis_harness.backoff."""

import unittest

from noesis_harness.backoff import schedule, jitter_none


class TestBackoff(unittest.TestCase):

    def test_attempt_zero_returns_base(self):
        self.assertEqual(schedule(0), 0.1)
        self.assertEqual(schedule(0, base=2.0), 2.0)

    def test_monotonic_increase(self):
        waits = [schedule(a) for a in range(6)]
        for i in range(1, len(waits)):
            self.assertGreater(waits[i], waits[i - 1])

    def test_cap_clamps(self):
        for a in range(5, 20):
            self.assertLessEqual(schedule(a), 5.0)
        self.assertEqual(schedule(100), 5.0)

    def test_factor_one_constant(self):
        waits = [schedule(a, factor=1.0) for a in range(10)]
        self.assertEqual(set(waits), {0.1})

    def test_determinism(self):
        for a in range(20):
            self.assertEqual(schedule(a), schedule(a))

    def test_custom_base_cap_factor(self):
        self.assertEqual(schedule(3, base=0.5, cap=10.0, factor=3.0),
                         min(10.0, 0.5 * (3.0 ** 3)))

    def test_cap_below_base(self):
        self.assertEqual(schedule(0, base=5.0, cap=1.0), 1.0)

    def test_fractional_attempt_not_used_but_safe(self):
        self.assertEqual(schedule(0, base=1.0, factor=0.5), 1.0)

    def test_jitter_none_identity(self):
        for v in (0.0, 0.1, 1.5, 9.9):
            self.assertEqual(jitter_none(v), v)

    def test_schedule_matches_formula(self):
        for a in range(8):
            expected = min(5.0, 0.1 * (2.0 ** a))
            self.assertAlmostEqual(schedule(a), expected)

    def test_increasing_until_cap(self):
        waits = [schedule(a) for a in range(7)]
        self.assertEqual(waits[-1], 5.0)
        self.assertTrue(all(waits[i] < 5.0 for i in range(6)))


if __name__ == "__main__":
    unittest.main()

"""Tests for noesis_harness.clock_utils.

Verifies that the clock helpers are pure, deterministic given input, and that
the elapsed-time formatting buckets behave as specified.
"""

import time
import unittest

from noesis_harness import clock_utils


class TestClockUtils(unittest.TestCase):

    def test_monotonic_increases(self):
        a = clock_utils.monotonic_ns()
        b = clock_utils.monotonic_ns()
        self.assertGreaterEqual(b, a)

    def test_monotonic_increases_over_sleep(self):
        a = clock_utils.monotonic_ns()
        time.sleep(0.01)
        b = clock_utils.monotonic_ns()
        self.assertGreater(b, a)

    def test_now_ns_is_int(self):
        self.assertIsInstance(clock_utils.now_ns(), int)

    def test_now_sec_is_float(self):
        self.assertIsInstance(clock_utils.now_sec(), float)

    def test_iso_utc_format(self):
        ts = 1_700_000_000
        self.assertEqual(clock_utils.iso_utc(ts), "2023-11-14T22:13:20Z")

    def test_iso_utc_default_is_utc(self):
        out = clock_utils.iso_utc()
        self.assertTrue(out.endswith("Z"))
        self.assertEqual(len(out), 20)

    def test_iso_utc_deterministic(self):
        ts = 1_699_000_000.123
        self.assertEqual(clock_utils.iso_utc(ts), clock_utils.iso_utc(ts))

    def test_iso_utc_zero(self):
        self.assertEqual(clock_utils.iso_utc(0), "1970-01-01T00:00:00Z")

    def test_format_elapsed_zero(self):
        self.assertEqual(clock_utils.format_elapsed(0), "0s")

    def test_format_elapsed_seconds(self):
        self.assertEqual(clock_utils.format_elapsed(5), "5s")

    def test_format_elapsed_minute_bucket(self):
        self.assertEqual(clock_utils.format_elapsed(90), "1m30s")

    def test_format_elapsed_hour_bucket(self):
        self.assertEqual(clock_utils.format_elapsed(3700), "1h1m")

    def test_format_elapsed_exactly_one_hour(self):
        self.assertEqual(clock_utils.format_elapsed(3600), "1h0m")

    def test_format_elapsed_none(self):
        self.assertEqual(clock_utils.format_elapsed(None), "0s")

    def test_format_elapsed_negative_clamped(self):
        self.assertEqual(clock_utils.format_elapsed(-10), "0s")

    def test_format_elapsed_deterministic(self):
        self.assertEqual(
            clock_utils.format_elapsed(125), clock_utils.format_elapsed(125)
        )


if __name__ == "__main__":
    unittest.main()

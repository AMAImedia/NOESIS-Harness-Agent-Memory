"""tests/test_rate_limiter.py

Unit tests for noesis_harness.rate_limiter (LoopX token-bucket pattern).
All timing-sensitive tests drive the limiter via the `now` override so they
are deterministic and never sleep.
"""

from __future__ import annotations

import threading
import time
import unittest

from noesis_harness.rate_limiter import RateLimiter


class TestRateLimiter(unittest.TestCase):
    def test_allow_when_full(self):
        rl = RateLimiter(capacity=5, refill_per_sec=1.0)
        self.assertTrue(rl.allow(5, now=0.0))
        self.assertEqual(rl.tokens(now=0.0), 0.0)

    def test_deny_when_empty(self):
        rl = RateLimiter(capacity=3, refill_per_sec=1.0)
        self.assertTrue(rl.allow(3, now=0.0))
        self.assertFalse(rl.allow(1, now=0.0))
        self.assertEqual(rl.tokens(now=0.0), 0.0)

    def test_refill_over_time(self):
        rl = RateLimiter(capacity=10, refill_per_sec=2.0)
        self.assertTrue(rl.allow(10, now=0.0))
        self.assertFalse(rl.allow(1, now=0.1))
        self.assertAlmostEqual(rl.tokens(now=0.5), 1.0, places=6)
        self.assertTrue(rl.allow(1, now=0.5))
        self.assertAlmostEqual(rl.tokens(now=1.0), 1.0, places=6)
        self.assertTrue(rl.allow(1, now=1.0))

    def test_partial_consume(self):
        rl = RateLimiter(capacity=5, refill_per_sec=1.0)
        self.assertTrue(rl.allow(2, now=0.0))
        self.assertTrue(rl.allow(2, now=0.0))
        self.assertFalse(rl.allow(2, now=0.0))
        self.assertAlmostEqual(rl.tokens(now=0.0), 1.0, places=6)

    def test_capacity_clamp_on_refill(self):
        rl = RateLimiter(capacity=4, refill_per_sec=10.0)
        self.assertTrue(rl.allow(4, now=0.0))
        self.assertAlmostEqual(rl.tokens(now=100.0), 4.0, places=6)
        self.assertTrue(rl.allow(4, now=100.0))

    def test_no_consumption_on_deny(self):
        rl = RateLimiter(capacity=2, refill_per_sec=1.0)
        self.assertTrue(rl.allow(2, now=0.0))
        self.assertFalse(rl.allow(5, now=0.0))
        self.assertFalse(rl.allow(1, now=0.0))
        self.assertEqual(rl.tokens(now=0.0), 0.0)

    def test_refill_rate_precision(self):
        rl = RateLimiter(capacity=100, refill_per_sec=0.5)
        self.assertTrue(rl.allow(100, now=0.0))
        self.assertAlmostEqual(rl.tokens(now=2.0), 1.0, places=6)
        self.assertAlmostEqual(rl.tokens(now=4.0), 2.0, places=6)

    def test_determinism_same_inputs(self):
        rl_a = RateLimiter(capacity=5, refill_per_sec=1.0)
        rl_b = RateLimiter(capacity=5, refill_per_sec=1.0)
        self.assertEqual(rl_a.allow(3, now=1.0), rl_b.allow(3, now=1.0))
        self.assertEqual(rl_a.tokens(now=3.0), rl_b.tokens(now=3.0))

    def test_thread_safety_smoke(self):
        rl = RateLimiter(capacity=200, refill_per_sec=1000.0)
        errors = []

        def worker(start, span):
            try:
                for i in range(span):
                    rl.allow(1, now=start + i * 0.001)
            except Exception as exc:  # pragma: no cover - defensive
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(t * 10, 20)) for t in range(10)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        self.assertEqual(errors, [])
        self.assertEqual(rl.tokens(now=1000.0), 200.0)

    def test_exact_boundary(self):
        rl = RateLimiter(capacity=3, refill_per_sec=1.0)
        self.assertTrue(rl.allow(3, now=0.0))
        self.assertFalse(rl.allow(1, now=0.0))
        self.assertTrue(rl.allow(1, now=1.0))

    def test_allow_default_n(self):
        rl = RateLimiter(capacity=2, refill_per_sec=1.0)
        self.assertTrue(rl.allow(now=0.0))
        self.assertTrue(rl.allow(now=0.0))
        self.assertFalse(rl.allow(now=0.0))

    def test_real_clock_sanity(self):
        rl = RateLimiter(capacity=3, refill_per_sec=100.0)
        self.assertTrue(rl.allow(3))
        self.assertFalse(rl.allow(1))
        time.sleep(0.05)
        self.assertTrue(rl.allow(1))


if __name__ == "__main__":
    unittest.main()

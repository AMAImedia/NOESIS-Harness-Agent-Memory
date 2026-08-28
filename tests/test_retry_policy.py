import unittest
from noesis_harness.retry_policy import RetryPolicy

class TestRetry(unittest.TestCase):
    def test_should_retry(self): p = RetryPolicy(3); self.assertTrue(p.should_retry(0)); self.assertTrue(p.should_retry(2)); self.assertFalse(p.should_retry(3))
    def test_backoff_base(self): self.assertAlmostEqual(RetryPolicy(3, base=0.1, cap=10, factor=2).backoff(0), 0.1)
    def test_backoff_growth(self): p = RetryPolicy(3, base=1, cap=10, factor=2); self.assertAlmostEqual(p.backoff(1), 2); self.assertAlmostEqual(p.backoff(2), 4)
    def test_cap(self): self.assertAlmostEqual(RetryPolicy(5, base=1, cap=3, factor=2).backoff(5), 3)
    def test_total(self): self.assertAlmostEqual(RetryPolicy(2, base=1, cap=10, factor=2).total_backoff(), 3)
    def test_factor_one(self): p = RetryPolicy(3, base=1, cap=10, factor=1); self.assertAlmostEqual(p.backoff(0), 1); self.assertAlmostEqual(p.backoff(2), 1)
    def test_zero_attempts(self): p = RetryPolicy(0); self.assertFalse(p.should_retry(0)); self.assertAlmostEqual(p.total_backoff(), 0)
    def test_invalid(self):
        with self.assertRaises(ValueError): RetryPolicy(-1)
    def test_determinism(self):
        a = RetryPolicy(3, base=0.2, cap=5, factor=1.5); b = RetryPolicy(3, base=0.2, cap=5, factor=1.5)
        self.assertEqual([a.backoff(i) for i in range(3)], [b.backoff(i) for i in range(3)])
    def test_many(self):
        p = RetryPolicy(10, base=0.1, cap=1, factor=2)
        for i in range(10): self.assertLessEqual(p.backoff(i), 1)

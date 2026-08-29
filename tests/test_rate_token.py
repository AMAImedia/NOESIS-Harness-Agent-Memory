import time, unittest
from noesis_harness.rate_token import TokenBucket

class TestRateToken(unittest.TestCase):
    def test_allow(self): tb = TokenBucket(3); self.assertTrue(tb.allow())
    def test_empty(self): tb = TokenBucket(1); tb.allow(); self.assertFalse(tb.allow())
    def test_refill(self): tb = TokenBucket(2, 100); tb.allow(); tb.allow(); self.assertFalse(tb.allow()); time.sleep(0.02); self.assertTrue(tb.allow())
    def test_tokens(self): tb = TokenBucket(3); self.assertEqual(tb.tokens(), 3.0)
    def test_invalid(self):
        with self.assertRaises(ValueError): TokenBucket(0)
    def test_len(self): tb = TokenBucket(3); self.assertEqual(len(tb), 3)
    def test_deterministic(self): tb = TokenBucket(3); tb.allow(); self.assertGreaterEqual(tb.tokens(), 0)
    def test_many(self): tb = TokenBucket(5); [tb.allow() for _ in range(5)]; self.assertFalse(tb.allow())
    def test_no_crash(self): tb = TokenBucket(10); [tb.allow() for _ in range(20)]
    def test_refill_rate(self): tb = TokenBucket(1, 1000); tb.allow(); time.sleep(0.005); self.assertTrue(tb.allow())

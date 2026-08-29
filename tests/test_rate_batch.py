import time, unittest
from noesis_harness.rate_batch import RateBatch

class TestRateBatch(unittest.TestCase):
    def test_allow_batch(self): rb = RateBatch(5); self.assertEqual(rb.allow_batch(3), 3)
    def test_partial(self): rb = RateBatch(3); self.assertEqual(rb.allow_batch(5), 3)
    def test_full(self): rb = RateBatch(2); rb.allow_batch(2); self.assertEqual(rb.allow_batch(1), 0)
    def test_refill(self): rb = RateBatch(2, 0.01); rb.allow_batch(2); time.sleep(0.02); self.assertEqual(rb.allow_batch(1), 1)
    def test_count(self): rb = RateBatch(5); rb.allow_batch(3); self.assertEqual(rb.count(), 3)
    def test_remaining(self): rb = RateBatch(5); rb.allow_batch(2); self.assertEqual(rb.remaining(), 3)
    def test_invalid(self):
        with self.assertRaises(ValueError): RateBatch(0)
    def test_deterministic(self): rb = RateBatch(5); rb.allow_batch(1); self.assertEqual(rb.count(), 1)
    def test_many(self): rb = RateBatch(10); rb.allow_batch(10); self.assertEqual(rb.count(), 10)
    def test_no_crash(self): rb = RateBatch(3); rb.allow_batch(5); rb.allow_batch(5)

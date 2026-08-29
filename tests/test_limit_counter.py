import time, unittest
from noesis_harness.limit_counter import LimitCounter

class TestLimitCounter(unittest.TestCase):
    def test_allow(self): lc = LimitCounter(3); self.assertTrue(lc.allow())
    def test_limit(self): lc = LimitCounter(2); lc.allow(); lc.allow(); self.assertFalse(lc.allow())
    def test_count(self): lc = LimitCounter(3); lc.allow(); lc.allow(); self.assertEqual(lc.count(), 2)
    def test_remaining(self): lc = LimitCounter(3); lc.allow(); self.assertEqual(lc.remaining(), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): LimitCounter(0)
    def test_window(self):
        lc = LimitCounter(2, 0.01); lc.allow(); lc.allow(); self.assertFalse(lc.allow())
        time.sleep(0.02); self.assertTrue(lc.allow())
    def test_deterministic(self): lc = LimitCounter(3); lc.allow(); self.assertEqual(lc.count(), 1)
    def test_many(self): lc = LimitCounter(5); [lc.allow() for _ in range(5)]; self.assertEqual(lc.count(), 5)
    def test_zero_limit(self): lc = LimitCounter(1); lc.allow(); self.assertFalse(lc.allow())
    def test_no_crash(self): lc = LimitCounter(10); [lc.allow() for _ in range(20)]

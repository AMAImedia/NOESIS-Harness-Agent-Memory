import time, unittest
from noesis_harness.window_rate import WindowRate

class TestWindowRate(unittest.TestCase):
    def test_allow(self): wr = WindowRate(3); self.assertTrue(wr.allow())
    def test_limit(self): wr = WindowRate(2); wr.allow(); wr.allow(); self.assertFalse(wr.allow())
    def test_refill(self): wr = WindowRate(2, 0.01); wr.allow(); wr.allow(); self.assertFalse(wr.allow()); time.sleep(0.02); self.assertTrue(wr.allow())
    def test_count(self): wr = WindowRate(3); wr.allow(); wr.allow(); self.assertEqual(wr.count(), 2)
    def test_remaining(self): wr = WindowRate(3); wr.allow(); self.assertEqual(wr.remaining(), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): WindowRate(0)
    def test_deterministic(self): wr = WindowRate(3); wr.allow(); self.assertEqual(wr.count(), 1)
    def test_many(self): wr = WindowRate(5); [wr.allow() for _ in range(5)]; self.assertFalse(wr.allow())
    def test_no_crash(self): wr = WindowRate(10); [wr.allow() for _ in range(20)]
    def test_window(self): wr = WindowRate(2, 0.01); wr.allow(); time.sleep(0.02); self.assertTrue(wr.allow())

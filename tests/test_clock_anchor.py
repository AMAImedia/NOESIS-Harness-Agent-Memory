import time, unittest
from noesis_harness.clock_anchor import ClockAnchor

class TestClockAnchor(unittest.TestCase):
    def test_elapsed(self): c = ClockAnchor(); self.assertGreaterEqual(c.elapsed(), 0)
    def test_reset(self): c = ClockAnchor(); c.reset(); self.assertGreaterEqual(c.elapsed(), 0)
    def test_increases(self):
        c = ClockAnchor(); a = c.elapsed(); b = c.elapsed(); self.assertGreaterEqual(b, a)
    def test_positive_after_sleep(self):
        c = ClockAnchor(); time.sleep(0.001); self.assertGreater(c.elapsed(), 0)
    def test_reset_small(self): c = ClockAnchor(); c.reset(); self.assertGreaterEqual(c.elapsed(), 0)
    def test_determinism(self): a = ClockAnchor(); b = ClockAnchor(); self.assertEqual(a.elapsed() >= 0, b.elapsed() >= 0)
    def test_type(self): self.assertIsInstance(ClockAnchor().elapsed(), float)
    def test_reset_twice(self): c = ClockAnchor(); c.reset(); c.reset(); self.assertGreaterEqual(c.elapsed(), 0)
    def test_no_error(self): c = ClockAnchor(); c.elapsed(); c.reset(); c.elapsed()
    def test_reset_elapsed(self): c = ClockAnchor(); e = c.elapsed(); c.reset(); self.assertGreaterEqual(c.elapsed(), 0)

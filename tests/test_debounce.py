import unittest
from noesis_harness.debounce import Debouncer

class TestDebouncer(unittest.TestCase):
    def test_first_true(self): self.assertTrue(Debouncer(10).should_emit("k", 0))
    def test_within_window_false(self):
        d = Debouncer(10); d.should_emit("k", 0); self.assertFalse(d.should_emit("k", 5))
    def test_after_window_true(self):
        d = Debouncer(10); d.should_emit("k", 0); self.assertTrue(d.should_emit("k", 10)); self.assertTrue(d.should_emit("k", 20))
    def test_per_key(self):
        d = Debouncer(10); d.should_emit("a", 0); self.assertTrue(d.should_emit("b", 0))
    def test_now_override(self):
        d = Debouncer(5); self.assertTrue(d.should_emit("k", 100)); self.assertFalse(d.should_emit("k", 102))
    def test_boundary(self):
        d = Debouncer(5); d.should_emit("k", 0); self.assertTrue(d.should_emit("k", 5))
    def test_reset_key(self):
        d = Debouncer(10); d.should_emit("k", 0); d.reset("k"); self.assertTrue(d.should_emit("k", 1))
    def test_reset_all(self):
        d = Debouncer(10); d.should_emit("a", 0); d.should_emit("b", 0); d.reset(); self.assertTrue(d.should_emit("a", 1))
    def test_zero_window_always(self):
        d = Debouncer(0); self.assertTrue(d.should_emit("k", 0)); self.assertTrue(d.should_emit("k", 0))
    def test_invalid(self):
        with self.assertRaises(ValueError): Debouncer(-1)
    def test_determinism(self):
        d1 = Debouncer(5); d2 = Debouncer(5)
        for t in [0, 2, 5, 6, 10]: self.assertEqual(d1.should_emit("k", t), d2.should_emit("k", t))

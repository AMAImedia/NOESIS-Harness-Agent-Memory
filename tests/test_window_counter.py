import unittest
from noesis_harness.window_counter import WindowCounter

class TestWindowCounter(unittest.TestCase):
    def test_add(self): w = WindowCounter(3); w.add(1); self.assertEqual(w.avg(), 1.0)
    def test_avg(self): w = WindowCounter(3); w.add(1); w.add(2); w.add(3); self.assertEqual(w.avg(), 2.0)
    def test_overflow(self): w = WindowCounter(2); w.add(1); w.add(2); w.add(3); self.assertEqual(w.avg(), 2.5)
    def test_total(self): w = WindowCounter(3); w.add(1); w.add(2); self.assertEqual(w.total(), 3)
    def test_count(self): w = WindowCounter(3); w.add(1); w.add(2); self.assertEqual(w.count(), 2)
    def test_empty(self): self.assertEqual(WindowCounter(3).avg(), 0.0)
    def test_invalid(self):
        with self.assertRaises(ValueError): WindowCounter(0)
    def test_len(self): w = WindowCounter(5); w.add(1); w.add(2); self.assertEqual(len(w), 2)
    def test_deterministic(self): w = WindowCounter(3); w.add(5); self.assertEqual(w.avg(), 5.0)
    def test_many(self): w = WindowCounter(3); [w.add(float(i)) for i in range(10)]; self.assertEqual(w.avg(), 8.0)

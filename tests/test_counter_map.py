import unittest
from noesis_harness.counter_map import CounterMap

class TestCounterMap(unittest.TestCase):
    def test_inc(self): c = CounterMap(); self.assertEqual(c.inc("a"), 1)
    def test_get_zero(self): self.assertEqual(CounterMap().get("x"), 0)
    def test_contains(self): c = CounterMap(); c.inc("a"); self.assertIn("a", c); self.assertNotIn("b", c)
    def test_invalid(self):
        with self.assertRaises(ValueError): CounterMap().inc("a", -1)
    def test_items(self): c = CounterMap(); c.inc("a"); c.inc("b"); self.assertEqual(set(c.items()), {("a", 1), ("b", 1)})
    def test_determinism(self): a = CounterMap(); b = CounterMap(); a.inc("x", 2); b.inc("x", 2); self.assertEqual(a.get("x"), b.get("x"))
    def test_cumulative(self): c = CounterMap(); c.inc("a"); c.inc("a"); c.inc("a"); self.assertEqual(c.get("a"), 3)
    def test_by(self): c = CounterMap(); self.assertEqual(c.inc("a", 5), 5)
    def test_no_mutation(self): c = CounterMap(); c.inc("a"); c.items(); self.assertTrue(c.inc("a") >= 1)
    def test_many(self):
        c = CounterMap()
        for i in range(5): c.inc(f"k{i}")
        self.assertEqual(len(c.items()), 5)

import unittest
from noesis_harness.ordered_dict import OrderedMap

class TestOrderedMap(unittest.TestCase):
    def test_put_get(self): m = OrderedMap(); m.put("a", 1); self.assertEqual(m.get("a"), 1)
    def test_order(self): m = OrderedMap(); m.put("a", 1); m.put("b", 2); m.put("c", 3); self.assertEqual(m.keys(), ["a", "b", "c"])
    def test_contains(self): m = OrderedMap(); m.put("a", 1); self.assertIn("a", m); self.assertNotIn("b", m)
    def test_default(self): m = OrderedMap(); self.assertIsNone(m.get("x")); self.assertEqual(m.get("x", 9), 9)
    def test_len(self): m = OrderedMap(); m.put("a", 1); self.assertEqual(len(m), 1)
    def test_overwrite_keeps_order(self): m = OrderedMap(); m.put("a", 1); m.put("b", 2); m.put("a", 9); self.assertEqual(m.keys(), ["a", "b"]); self.assertEqual(m.get("a"), 9)
    def test_determinism(self): a = OrderedMap(); b = OrderedMap(); a.put("x", 1); b.put("x", 1); self.assertEqual(a.keys(), b.keys())
    def test_many(self):
        m = OrderedMap()
        for i in range(5): m.put(f"k{i}", i)
        self.assertEqual(len(m.keys()), 5)
    def test_no_mutation(self): m = OrderedMap(); m.put("a", 1); m.get("a"); self.assertIn("a", m)
    def test_reinsert(self): m = OrderedMap(); m.put("a", 1); m.put("a", 2); self.assertEqual(m.keys(), ["a"])

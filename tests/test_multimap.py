import unittest
from noesis_harness.multimap import MultiMap

class TestMultiMap(unittest.TestCase):
    def test_put_get(self): m = MultiMap(); m.put("a", 1); m.put("a", 2); self.assertEqual(m.get("a"), [1, 2])
    def test_keys(self): m = MultiMap(); m.put("a", 1); m.put("b", 2); self.assertEqual(set(m.keys()), {"a", "b"})
    def test_empty(self): self.assertEqual(MultiMap().get("x"), [])
    def test_contains(self): m = MultiMap(); m.put("a", 1); self.assertIn("a", m); self.assertNotIn("b", m)
    def test_determinism(self): a = MultiMap(); b = MultiMap(); a.put("a", 1); b.put("a", 1); self.assertEqual(a.get("a"), b.get("a"))
    def test_many(self):
        m = MultiMap()
        for i in range(5): m.put("k", i)
        self.assertEqual(len(m.get("k")), 5)
    def test_distinct(self): m = MultiMap(); m.put("a", 1); m.put("b", 2); self.assertEqual(m.get("a"), [1])
    def test_no_mutation(self): m = MultiMap(); m.put("a", 1); m.get("a"); self.assertIn("a", m)
    def test_order(self): m = MultiMap(); m.put("a", 1); m.put("a", 2); m.put("a", 3); self.assertEqual(m.get("a"), [1, 2, 3])
    def test_values(self): m = MultiMap(); m.put("a", "x"); self.assertEqual(m.get("a"), ["x"])

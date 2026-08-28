import unittest
from noesis_harness.default_dict import DefaultMap

class TestDefaultMap(unittest.TestCase):
    def test_default_zero(self): m = DefaultMap(); self.assertEqual(m.get("x"), 0)
    def test_put_get(self): m = DefaultMap(); m.put("a", 5); self.assertEqual(m.get("a"), 5)
    def test_keys(self): m = DefaultMap(); m.put("a", 1); self.assertEqual(m.keys(), ["a"])
    def test_contains(self): m = DefaultMap(); m.put("a", 1); self.assertIn("a", m); self.assertNotIn("b", m)
    def test_len(self): m = DefaultMap(); m.put("a", 1); self.assertEqual(len(m), 1)
    def test_factory_list(self): m = DefaultMap(list); m.get("x").append(1); self.assertEqual(m.get("x"), [1])
    def test_determinism(self): a = DefaultMap(); b = DefaultMap(); a.put("x", 1); b.put("x", 1); self.assertEqual(a.get("x"), b.get("x"))
    def test_many(self):
        m = DefaultMap()
        for i in range(5): m.put(f"k{i}", i)
        self.assertEqual(len(m.keys()), 5)
    def test_no_mutation(self): m = DefaultMap(); m.put("a", 1); m.get("a"); self.assertIn("a", m)
    def test_default_access(self): m = DefaultMap(); self.assertEqual(m.get("missing"), 0)

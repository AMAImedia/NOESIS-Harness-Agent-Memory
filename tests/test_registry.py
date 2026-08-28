import unittest
from noesis_harness.registry import Registry

class TestRegistry(unittest.TestCase):
    def test_put_get(self): r = Registry(); r.put("a", 1); self.assertEqual(r.get("a"), 1)
    def test_has(self): r = Registry(); r.put("a", 1); self.assertTrue(r.has("a")); self.assertFalse(r.has("b"))
    def test_default(self): r = Registry(); self.assertIsNone(r.get("x")); self.assertEqual(r.get("x", 9), 9)
    def test_empty_name(self):
        with self.assertRaises(ValueError): Registry().put("", 1)
    def test_keys(self): r = Registry(); r.put("a", 1); r.put("b", 2); self.assertEqual(set(r.keys()), {"a", "b"})
    def test_overwrite(self): r = Registry(); r.put("a", 1); r.put("a", 2); self.assertEqual(r.get("a"), 2)
    def test_no_mutation(self): r = Registry(); r.put("a", 1); r.get("a"); self.assertTrue(r.has("a"))
    def test_determinism(self): r = Registry(); r.put("a", 1); self.assertEqual(r.get("a"), r.get("a"))
    def test_many(self):
        r = Registry()
        for i in range(5): r.put(f"k{i}", i)
        self.assertEqual(len(r.keys()), 5)
    def test_value(self): r = Registry(); r.put("s", "hi"); self.assertEqual(r.get("s"), "hi")

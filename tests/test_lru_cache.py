import unittest
from noesis_harness.lru_cache import LRUCache

class TestLRUCache(unittest.TestCase):
    def test_put_get(self): c = LRUCache(2); c.put("a", 1); self.assertEqual(c.get("a"), 1)
    def test_evict(self): c = LRUCache(2); c.put("a", 1); c.put("b", 2); c.put("c", 3); self.assertNotIn("a", c); self.assertIn("c", c)
    def test_default(self): c = LRUCache(2); self.assertIsNone(c.get("x")); self.assertEqual(c.get("x", 9), 9)
    def test_capacity(self): c = LRUCache(3); [c.put(i, i) for i in range(5)]; self.assertEqual(len(c), 3)
    def test_invalid(self):
        with self.assertRaises(ValueError): LRUCache(0)
    def test_recent_used(self):
        c = LRUCache(2); c.put("a", 1); c.put("b", 2); c.get("a"); c.put("c", 3); self.assertIn("a", c); self.assertNotIn("b", c)
    def test_update(self):
        c = LRUCache(2); c.put("a", 1); c.put("a", 2); self.assertEqual(c.get("a"), 2); self.assertEqual(len(c), 1)
    def test_determinism(self):
        a = LRUCache(2); b = LRUCache(2); a.put("a", 1); b.put("a", 1); self.assertEqual(a.get("a"), b.get("a"))
    def test_many(self):
        c = LRUCache(5)
        for i in range(10): c.put(i, i)
        self.assertEqual(len(c), 5)
    def test_contains(self): c = LRUCache(1); c.put("a", 1); self.assertIn("a", c); self.assertNotIn("b", c)

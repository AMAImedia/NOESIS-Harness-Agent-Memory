import unittest
from noesis_harness.cache_util import CacheUtil

class TestCacheUtil(unittest.TestCase):
    def test_put_get(self): c = CacheUtil(); c.put("k", 1); self.assertEqual(c.get("k"), 1)
    def test_missing(self): self.assertIsNone(CacheUtil().get("x"))
    def test_invalidate(self): c = CacheUtil(); c.put("a", 1); self.assertTrue(c.invalidate("a")); self.assertIsNone(c.get("a"))
    def test_invalidate_missing(self): self.assertFalse(CacheUtil().invalidate("x"))
    def test_clear(self): c = CacheUtil(); c.put("a", 1); c.put("b", 2); self.assertEqual(c.clear(), 2); self.assertEqual(len(c), 0)
    def test_maxsize(self): c = CacheUtil(2); c.put("a", 1); c.put("b", 2); c.put("c", 3); self.assertNotIn("a", c); self.assertEqual(len(c), 2)
    def test_update(self): c = CacheUtil(); c.put("a", 1); c.put("a", 2); self.assertEqual(c.get("a"), 2); self.assertEqual(len(c), 1)
    def test_invalid(self):
        with self.assertRaises(ValueError): CacheUtil(0)
    def test_deterministic(self): c = CacheUtil(); c.put("a", 1); self.assertEqual(c.get("a"), c.get("a"))
    def test_many(self): c = CacheUtil(10); [c.put(f"k{i}", i) for i in range(10)]; self.assertEqual(len(c), 10)
    def test_contains(self): c = CacheUtil(); c.put("a", 1); self.assertIn("a", c); self.assertNotIn("b", c)

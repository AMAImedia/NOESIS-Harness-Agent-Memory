import time, unittest
from noesis_harness.cache_wrap import TTLCache

class TestCacheWrap(unittest.TestCase):
    def test_put_get(self): c = TTLCache(10); c.put("k", 1); self.assertEqual(c.get("k"), 1)
    def test_missing(self): self.assertIsNone(TTLCache(10).get("x"))
    def test_invalidate(self): c = TTLCache(10); c.put("a", 1); self.assertTrue(c.invalidate("a")); self.assertIsNone(c.get("a"))
    def test_invalidate_missing(self): self.assertFalse(TTLCache(10).invalidate("x"))
    def test_clear(self): c = TTLCache(10); c.put("a", 1); c.put("b", 2); self.assertEqual(c.clear(), 2); self.assertEqual(len(c), 0)
    def test_ttl(self): c = TTLCache(0.01); c.put("a", 1); time.sleep(0.02); self.assertIsNone(c.get("a"))
    def test_len(self): c = TTLCache(10); c.put("a", 1); c.put("b", 2); self.assertEqual(len(c), 2)
    def test_invalid_ttl(self):
        with self.assertRaises(ValueError): TTLCache(0)
    def test_determinism(self): c = TTLCache(10); c.put("a", 1); self.assertEqual(c.get("a"), c.get("a"))
    def test_many(self): c = TTLCache(10); [c.put(f"k{i}", i) for i in range(5)]; self.assertEqual(len(c), 5)

import unittest
from noesis_harness.ttl_cache import TTLCache

class TestTTLCache(unittest.TestCase):
    def test_put_get(self): c = TTLCache(10); c.put("k", 1, now=0); self.assertEqual(c.get("k", now=5), 1)
    def test_expired(self): c = TTLCache(5); c.put("k", 1, now=0); self.assertIsNone(c.get("k", now=5)); self.assertIsNone(c.get("k", now=6))
    def test_len(self): c = TTLCache(10); c.put("a", 1, now=0); c.put("b", 2, now=0); self.assertEqual(len(c), 2)
    def test_missing(self): self.assertIsNone(TTLCache(10).get("nope", now=0))
    def test_overwrite(self): c = TTLCache(10); c.put("k", 1, now=0); c.put("k", 2, now=1); self.assertEqual(c.get("k", now=2), 2)
    def test_boundary(self): c = TTLCache(5); c.put("k", 1, now=0); self.assertIsNone(c.get("k", now=5))
    def test_invalid(self):
        with self.assertRaises(ValueError): TTLCache(0)
    def test_determinism(self):
        a = TTLCache(10); b = TTLCache(10); a.put("k", 1, now=0); b.put("k", 1, now=0)
        self.assertEqual(a.get("k", now=5), b.get("k", now=5))
    def test_expire_removes(self): c = TTLCache(5); c.put("k", 1, now=0); c.get("k", now=10); self.assertEqual(len(c), 0)
    def test_many(self):
        c = TTLCache(100)
        for i in range(20): c.put(str(i), i, now=0)
        self.assertEqual(len(c), 20)

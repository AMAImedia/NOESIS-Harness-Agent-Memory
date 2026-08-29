import time, unittest
from noesis_harness.memoize_ttl import MemoTTL

class TestMemoTTL(unittest.TestCase):
    def test_put_get(self): m = MemoTTL(10); m.put("k", 1); self.assertEqual(m.get("k"), 1)
    def test_missing(self): self.assertIsNone(MemoTTL(10).get("x"))
    def test_invalidate(self): m = MemoTTL(10); m.put("a", 1); self.assertTrue(m.invalidate("a")); self.assertIsNone(m.get("a"))
    def test_invalidate_missing(self): self.assertFalse(MemoTTL(10).invalidate("x"))
    def test_clear(self): m = MemoTTL(10); m.put("a", 1); m.put("b", 2); self.assertEqual(m.clear(), 2); self.assertEqual(len(m), 0)
    def test_ttl(self): m = MemoTTL(0.01); m.put("a", 1); time.sleep(0.02); self.assertIsNone(m.get("a"))
    def test_len(self): m = MemoTTL(10); m.put("a", 1); m.put("b", 2); self.assertEqual(len(m), 2)
    def test_invalid_ttl(self):
        with self.assertRaises(ValueError): MemoTTL(0)
    def test_determinism(self): m = MemoTTL(10); m.put("a", 1); self.assertEqual(m.get("a"), m.get("a"))
    def test_many(self): m = MemoTTL(10); [m.put(f"k{i}", i) for i in range(5)]; self.assertEqual(len(m), 5)

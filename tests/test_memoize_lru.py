import unittest
from noesis_harness.memoize_lru import MemoLRU

class TestMemoLRU(unittest.TestCase):
    def test_put_get(self): m = MemoLRU(3); m.put("k", 1); self.assertEqual(m.get("k"), 1)
    def test_missing(self): self.assertIsNone(MemoLRU(3).get("x"))
    def test_evict(self): m = MemoLRU(2); m.put("a", 1); m.put("b", 2); m.put("c", 3); self.assertNotIn("a", m); self.assertIn("c", m)
    def test_lru_order(self): m = MemoLRU(2); m.put("a", 1); m.put("b", 2); m.get("a"); m.put("c", 3); self.assertIn("a", m); self.assertNotIn("b", m)
    def test_invalidate(self): m = MemoLRU(3); m.put("a", 1); self.assertTrue(m.invalidate("a")); self.assertFalse(m.invalidate("a"))
    def test_clear(self): m = MemoLRU(3); m.put("a", 1); m.put("b", 2); self.assertEqual(m.clear(), 2); self.assertEqual(len(m), 0)
    def test_len(self): m = MemoLRU(3); m.put("a", 1); m.put("b", 2); self.assertEqual(len(m), 2)
    def test_contains(self): m = MemoLRU(3); m.put("a", 1); self.assertIn("a", m); self.assertNotIn("b", m)
    def test_invalid(self):
        with self.assertRaises(ValueError): MemoLRU(0)
    def test_deterministic(self): m = MemoLRU(3); m.put("a", 1); self.assertEqual(m.get("a"), m.get("a"))
    def test_many(self): m = MemoLRU(5); [m.put(f"k{i}", i) for i in range(10)]; self.assertEqual(len(m), 5)

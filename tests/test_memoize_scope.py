import unittest
from noesis_harness.memoize_scope import MemoScope

class TestMemoScope(unittest.TestCase):
    def test_put_get(self): m = MemoScope(); m.put("s1", "k", 1); self.assertEqual(m.get("s1", "k"), 1)
    def test_missing(self): self.assertIsNone(MemoScope().get("s1", "k"))
    def test_invalidate_scope(self): m = MemoScope(); m.put("s1", "a", 1); m.put("s1", "b", 2); self.assertEqual(m.invalidate_scope("s1"), 2); self.assertIsNone(m.get("s1", "a"))
    def test_invalidate_key(self): m = MemoScope(); m.put("s1", "a", 1); self.assertTrue(m.invalidate_key("s1", "a")); self.assertFalse(m.invalidate_key("s1", "a"))
    def test_clear(self): m = MemoScope(); m.put("s1", "a", 1); m.put("s2", "b", 2); self.assertEqual(m.clear(), 2); self.assertEqual(len(m), 0)
    def test_len(self): m = MemoScope(); m.put("s1", "a", 1); m.put("s1", "b", 2); self.assertEqual(len(m), 2)
    def test_no_mutation(self): m = MemoScope(); m.put("s1", "a", 1); m.get("s1", "a"); self.assertEqual(len(m), 1)
    def test_deterministic(self): m = MemoScope(); m.put("s1", "k", 5); self.assertEqual(m.get("s1", "k"), m.get("s1", "k"))
    def test_many(self): m = MemoScope(); [m.put(f"s{i}", f"k{i}", i) for i in range(5)]; self.assertEqual(len(m), 5)
    def test_overwrite(self): m = MemoScope(); m.put("s1", "a", 1); m.put("s1", "a", 2); self.assertEqual(m.get("s1", "a"), 2)

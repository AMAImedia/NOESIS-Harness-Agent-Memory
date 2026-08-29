import unittest
from noesis_harness.memoize_core import MemoCore

class TestMemoCore(unittest.TestCase):
    def test_core(self): m = MemoCore(); self.assertEqual(m.core("k", 1), 1)
    def test_existing(self): m = MemoCore(); m.core("k", 1); self.assertEqual(m.core("k", 2), 1)
    def test_get(self): m = MemoCore(); m.set("k", 1); self.assertEqual(m.get("k"), 1)
    def test_get_default(self): self.assertEqual(MemoCore().get("x", 5), 5)
    def test_invalidate(self): m = MemoCore(); m.set("k", 1); self.assertTrue(m.invalidate("k")); self.assertFalse(m.invalidate("k"))
    def test_clear(self): m = MemoCore(); m.set("a", 1); m.set("b", 2); self.assertEqual(m.clear(), 2); self.assertEqual(len(m), 0)
    def test_len(self): m = MemoCore(); m.set("a", 1); m.set("b", 2); self.assertEqual(len(m), 2)
    def test_contains(self): m = MemoCore(); m.set("a", 1); self.assertIn("a", m); self.assertNotIn("b", m)
    def test_deterministic(self): m = MemoCore(); m.set("a", 1); self.assertEqual(m.get("a"), m.get("a"))
    def test_many(self): m = MemoCore(); [m.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(m), 5)

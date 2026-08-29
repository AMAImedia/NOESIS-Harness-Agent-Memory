import unittest
from noesis_harness.memoize_adapter import MemoAdapter

class TestMemoAdapter(unittest.TestCase):
    def test_adapt(self): m = MemoAdapter(); self.assertEqual(m.adapt("k", 1), 1)
    def test_existing(self): m = MemoAdapter(); m.adapt("k", 1); self.assertEqual(m.adapt("k", 2), 1)
    def test_get(self): m = MemoAdapter(); m.set("k", 1); self.assertEqual(m.get("k"), 1)
    def test_get_default(self): self.assertEqual(MemoAdapter().get("x", 5), 5)
    def test_invalidate(self): m = MemoAdapter(); m.set("k", 1); self.assertTrue(m.invalidate("k")); self.assertFalse(m.invalidate("k"))
    def test_clear(self): m = MemoAdapter(); m.set("a", 1); m.set("b", 2); self.assertEqual(m.clear(), 2); self.assertEqual(len(m), 0)
    def test_len(self): m = MemoAdapter(); m.set("a", 1); m.set("b", 2); self.assertEqual(len(m), 2)
    def test_contains(self): m = MemoAdapter(); m.set("a", 1); self.assertIn("a", m); self.assertNotIn("b", m)
    def test_deterministic(self): m = MemoAdapter(); m.set("a", 1); self.assertEqual(m.get("a"), m.get("a"))
    def test_many(self): m = MemoAdapter(); [m.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(m), 5)

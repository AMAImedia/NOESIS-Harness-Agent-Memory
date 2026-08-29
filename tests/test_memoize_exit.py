import unittest
from noesis_harness.memoize_exit import MemoExit

class TestMemoExit(unittest.TestCase):
    def test_exit(self): m = MemoExit(); self.assertEqual(m.exit("k", 1), 1)
    def test_existing(self): m = MemoExit(); m.exit("k", 1); self.assertEqual(m.exit("k", 2), 1)
    def test_get(self): m = MemoExit(); m.set("k", 1); self.assertEqual(m.get("k"), 1)
    def test_get_default(self): self.assertEqual(MemoExit().get("x", 5), 5)
    def test_invalidate(self): m = MemoExit(); m.set("k", 1); self.assertTrue(m.invalidate("k")); self.assertFalse(m.invalidate("k"))
    def test_clear(self): m = MemoExit(); m.set("a", 1); m.set("b", 2); self.assertEqual(m.clear(), 2); self.assertEqual(len(m), 0)
    def test_len(self): m = MemoExit(); m.set("a", 1); m.set("b", 2); self.assertEqual(len(m), 2)
    def test_contains(self): m = MemoExit(); m.set("a", 1); self.assertIn("a", m); self.assertNotIn("b", m)
    def test_deterministic(self): m = MemoExit(); m.set("a", 1); self.assertEqual(m.get("a"), m.get("a"))
    def test_many(self): m = MemoExit(); [m.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(m), 5)

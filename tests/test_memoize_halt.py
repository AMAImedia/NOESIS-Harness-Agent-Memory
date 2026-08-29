import unittest
from noesis_harness.memoize_halt import MemoHalt

class TestMemoHalt(unittest.TestCase):
    def test_halt(self): m = MemoHalt(); self.assertEqual(m.halt("k", 1), 1)
    def test_existing(self): m = MemoHalt(); m.halt("k", 1); self.assertEqual(m.halt("k", 2), 1)
    def test_get(self): m = MemoHalt(); m.set("k", 1); self.assertEqual(m.get("k"), 1)
    def test_get_default(self): self.assertEqual(MemoHalt().get("x", 5), 5)
    def test_invalidate(self): m = MemoHalt(); m.set("k", 1); self.assertTrue(m.invalidate("k")); self.assertFalse(m.invalidate("k"))
    def test_clear(self): m = MemoHalt(); m.set("a", 1); m.set("b", 2); self.assertEqual(m.clear(), 2); self.assertEqual(len(m), 0)
    def test_len(self): m = MemoHalt(); m.set("a", 1); m.set("b", 2); self.assertEqual(len(m), 2)
    def test_contains(self): m = MemoHalt(); m.set("a", 1); self.assertIn("a", m); self.assertNotIn("b", m)
    def test_deterministic(self): m = MemoHalt(); m.set("a", 1); self.assertEqual(m.get("a"), m.get("a"))
    def test_many(self): m = MemoHalt(); [m.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(m), 5)

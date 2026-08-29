import unittest
from noesis_harness.memoize_wait import MemoWait

class TestMemoWait(unittest.TestCase):
    def test_wait(self): m = MemoWait(); self.assertEqual(m.wait("k", 1), 1)
    def test_existing(self): m = MemoWait(); m.wait("k", 1); self.assertEqual(m.wait("k", 2), 1)
    def test_get(self): m = MemoWait(); m.set("k", 1); self.assertEqual(m.get("k"), 1)
    def test_get_default(self): self.assertEqual(MemoWait().get("x", 5), 5)
    def test_invalidate(self): m = MemoWait(); m.set("k", 1); self.assertTrue(m.invalidate("k")); self.assertFalse(m.invalidate("k"))
    def test_clear(self): m = MemoWait(); m.set("a", 1); m.set("b", 2); self.assertEqual(m.clear(), 2); self.assertEqual(len(m), 0)
    def test_len(self): m = MemoWait(); m.set("a", 1); m.set("b", 2); self.assertEqual(len(m), 2)
    def test_contains(self): m = MemoWait(); m.set("a", 1); self.assertIn("a", m); self.assertNotIn("b", m)
    def test_deterministic(self): m = MemoWait(); m.set("a", 1); self.assertEqual(m.get("a"), m.get("a"))
    def test_many(self): m = MemoWait(); [m.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(m), 5)

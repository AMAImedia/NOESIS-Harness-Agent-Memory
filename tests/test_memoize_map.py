import unittest
from noesis_harness.memoize_map import MemoMap

class TestMemoMap(unittest.TestCase):
    def test_mapping(self): m = MemoMap(); self.assertEqual(m.mapping("k", 1), 1)
    def test_existing(self): m = MemoMap(); m.mapping("k", 1); self.assertEqual(m.mapping("k", 2), 1)
    def test_get(self): m = MemoMap(); m.set("k", 1); self.assertEqual(m.get("k"), 1)
    def test_get_default(self): self.assertEqual(MemoMap().get("x", 5), 5)
    def test_invalidate(self): m = MemoMap(); m.set("k", 1); self.assertTrue(m.invalidate("k")); self.assertFalse(m.invalidate("k"))
    def test_clear(self): m = MemoMap(); m.set("a", 1); m.set("b", 2); self.assertEqual(m.clear(), 2); self.assertEqual(len(m), 0)
    def test_len(self): m = MemoMap(); m.set("a", 1); m.set("b", 2); self.assertEqual(len(m), 2)
    def test_contains(self): m = MemoMap(); m.set("a", 1); self.assertIn("a", m); self.assertNotIn("b", m)
    def test_deterministic(self): m = MemoMap(); m.set("a", 1); self.assertEqual(m.get("a"), m.get("a"))
    def test_many(self): m = MemoMap(); [m.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(m), 5)

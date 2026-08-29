import unittest
from noesis_harness.memoize_bind import MemoBind

class TestMemoBind(unittest.TestCase):
    def test_binding(self): m = MemoBind(); self.assertEqual(m.binding("k", 1), 1)
    def test_existing(self): m = MemoBind(); m.binding("k", 1); self.assertEqual(m.binding("k", 2), 1)
    def test_get(self): m = MemoBind(); m.set("k", 1); self.assertEqual(m.get("k"), 1)
    def test_get_default(self): self.assertEqual(MemoBind().get("x", 5), 5)
    def test_invalidate(self): m = MemoBind(); m.set("k", 1); self.assertTrue(m.invalidate("k")); self.assertFalse(m.invalidate("k"))
    def test_clear(self): m = MemoBind(); m.set("a", 1); m.set("b", 2); self.assertEqual(m.clear(), 2); self.assertEqual(len(m), 0)
    def test_len(self): m = MemoBind(); m.set("a", 1); m.set("b", 2); self.assertEqual(len(m), 2)
    def test_contains(self): m = MemoBind(); m.set("a", 1); self.assertIn("a", m); self.assertNotIn("b", m)
    def test_deterministic(self): m = MemoBind(); m.set("a", 1); self.assertEqual(m.get("a"), m.get("a"))
    def test_many(self): m = MemoBind(); [m.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(m), 5)

import unittest
from noesis_harness.memoize_halt_done import MemoHaltDone

class TestMemoHaltDone(unittest.TestCase):
    def test_halt_done(self): m = MemoHaltDone(); self.assertEqual(m.halt_done("k", 1), 1)
    def test_existing(self): m = MemoHaltDone(); m.halt_done("k", 1); self.assertEqual(m.halt_done("k", 2), 1)
    def test_get(self): m = MemoHaltDone(); m.set("k", 1); self.assertEqual(m.get("k"), 1)
    def test_get_default(self): self.assertEqual(MemoHaltDone().get("x", 5), 5)
    def test_invalidate(self): m = MemoHaltDone(); m.set("k", 1); self.assertTrue(m.invalidate("k")); self.assertFalse(m.invalidate("k"))
    def test_clear(self): m = MemoHaltDone(); m.set("a", 1); m.set("b", 2); self.assertEqual(m.clear(), 2); self.assertEqual(len(m), 0)
    def test_len(self): m = MemoHaltDone(); m.set("a", 1); m.set("b", 2); self.assertEqual(len(m), 2)
    def test_contains(self): m = MemoHaltDone(); m.set("a", 1); self.assertIn("a", m); self.assertNotIn("b", m)
    def test_deterministic(self): m = MemoHaltDone(); m.set("a", 1); self.assertEqual(m.get("a"), m.get("a"))
    def test_many(self): m = MemoHaltDone(); [m.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(m), 5)

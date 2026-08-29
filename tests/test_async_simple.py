import unittest
from noesis_harness.async_simple import AsyncSimple

class TestAsyncSimple(unittest.TestCase):
    def test_remember(self): m = AsyncSimple(); self.assertEqual(m.remember("a", lambda: 1), 1)
    def test_cached(self): m = AsyncSimple(); m.remember("a", lambda: 1); self.assertEqual(m.remember("a", lambda: 2), 1)
    def test_get(self): m = AsyncSimple(); m.set("k", 1); self.assertEqual(m.get("k"), 1)
    def test_get_default(self): self.assertEqual(AsyncSimple().get("x", 5), 5)
    def test_invalidate(self): m = AsyncSimple(); m.set("k", 1); self.assertTrue(m.invalidate("k")); self.assertFalse(m.invalidate("k"))
    def test_clear(self): m = AsyncSimple(); m.set("a", 1); m.set("b", 2); self.assertEqual(m.clear(), 2); self.assertEqual(len(m), 0)
    def test_len(self): m = AsyncSimple(); m.set("a", 1); m.set("b", 2); self.assertEqual(len(m), 2)
    def test_deterministic(self): m = AsyncSimple(); m.set("a", 1); self.assertEqual(m.get("a"), m.get("a"))
    def test_many(self): m = AsyncSimple(); [m.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(m), 5)
    def test_no_crash(self): AsyncSimple().get("x")

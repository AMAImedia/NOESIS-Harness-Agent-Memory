import unittest
from noesis_harness.async_done import AsyncDone

class TestAsyncDone(unittest.TestCase):
    def test_done(self): m = AsyncDone(); self.assertEqual(m.done("a", lambda: 1), 1)
    def test_cached(self): m = AsyncDone(); m.done("a", lambda: 1); self.assertEqual(m.done("a", lambda: 2), 1)
    def test_get(self): m = AsyncDone(); m.set("k", 1); self.assertEqual(m.get("k"), 1)
    def test_get_default(self): self.assertEqual(AsyncDone().get("x", 5), 5)
    def test_invalidate(self): m = AsyncDone(); m.set("k", 1); self.assertTrue(m.invalidate("k")); self.assertFalse(m.invalidate("k"))
    def test_clear(self): m = AsyncDone(); m.set("a", 1); m.set("b", 2); self.assertEqual(m.clear(), 2); self.assertEqual(len(m), 0)
    def test_len(self): m = AsyncDone(); m.set("a", 1); m.set("b", 2); self.assertEqual(len(m), 2)
    def test_deterministic(self): m = AsyncDone(); m.set("a", 1); self.assertEqual(m.get("a"), m.get("a"))
    def test_many(self): m = AsyncDone(); [m.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(m), 5)
    def test_no_crash(self): AsyncDone().get("x")

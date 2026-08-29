import unittest
from noesis_harness.async_quit import AsyncQuit

class TestAsyncQuit(unittest.TestCase):
    def test_quit(self): m = AsyncQuit(); self.assertEqual(m.quit("a", lambda: 1), 1)
    def test_cached(self): m = AsyncQuit(); m.quit("a", lambda: 1); self.assertEqual(m.quit("a", lambda: 2), 1)
    def test_get(self): m = AsyncQuit(); m.set("k", 1); self.assertEqual(m.get("k"), 1)
    def test_get_default(self): self.assertEqual(AsyncQuit().get("x", 5), 5)
    def test_invalidate(self): m = AsyncQuit(); m.set("k", 1); self.assertTrue(m.invalidate("k")); self.assertFalse(m.invalidate("k"))
    def test_clear(self): m = AsyncQuit(); m.set("a", 1); m.set("b", 2); self.assertEqual(m.clear(), 2); self.assertEqual(len(m), 0)
    def test_len(self): m = AsyncQuit(); m.set("a", 1); m.set("b", 2); self.assertEqual(len(m), 2)
    def test_deterministic(self): m = AsyncQuit(); m.set("a", 1); self.assertEqual(m.get("a"), m.get("a"))
    def test_many(self): m = AsyncQuit(); [m.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(m), 5)
    def test_no_crash(self): AsyncQuit().get("x")

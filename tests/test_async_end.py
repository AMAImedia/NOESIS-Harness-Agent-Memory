import unittest
from noesis_harness.async_end import AsyncEnd

class TestAsyncEnd(unittest.TestCase):
    def test_end(self): m = AsyncEnd(); self.assertEqual(m.end("a", lambda: 1), 1)
    def test_cached(self): m = AsyncEnd(); m.end("a", lambda: 1); self.assertEqual(m.end("a", lambda: 2), 1)
    def test_get(self): m = AsyncEnd(); m.set("k", 1); self.assertEqual(m.get("k"), 1)
    def test_get_default(self): self.assertEqual(AsyncEnd().get("x", 5), 5)
    def test_invalidate(self): m = AsyncEnd(); m.set("k", 1); self.assertTrue(m.invalidate("k")); self.assertFalse(m.invalidate("k"))
    def test_clear(self): m = AsyncEnd(); m.set("a", 1); m.set("b", 2); self.assertEqual(m.clear(), 2); self.assertEqual(len(m), 0)
    def test_len(self): m = AsyncEnd(); m.set("a", 1); m.set("b", 2); self.assertEqual(len(m), 2)
    def test_deterministic(self): m = AsyncEnd(); m.set("a", 1); self.assertEqual(m.get("a"), m.get("a"))
    def test_many(self): m = AsyncEnd(); [m.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(m), 5)
    def test_no_crash(self): AsyncEnd().get("x")

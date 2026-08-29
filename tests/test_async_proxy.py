import unittest
from noesis_harness.async_proxy import AsyncProxy

class TestAsyncProxy(unittest.TestCase):
    def test_get_or_compute(self): m = AsyncProxy(); self.assertEqual(m.get_or_compute("a", lambda: 1), 1)
    def test_cached(self): m = AsyncProxy(); m.get_or_compute("a", lambda: 1); self.assertEqual(m.get_or_compute("a", lambda: 2), 1)
    def test_get(self): m = AsyncProxy(); m.set("k", 1); self.assertEqual(m.get("k"), 1)
    def test_get_default(self): self.assertEqual(AsyncProxy().get("x", 5), 5)
    def test_invalidate(self): m = AsyncProxy(); m.set("k", 1); self.assertTrue(m.invalidate("k")); self.assertFalse(m.invalidate("k"))
    def test_clear(self): m = AsyncProxy(); m.set("a", 1); m.set("b", 2); self.assertEqual(m.clear(), 2); self.assertEqual(len(m), 0)
    def test_len(self): m = AsyncProxy(); m.set("a", 1); m.set("b", 2); self.assertEqual(len(m), 2)
    def test_deterministic(self): m = AsyncProxy(); m.set("a", 1); self.assertEqual(m.get("a"), m.get("a"))
    def test_many(self): m = AsyncProxy(); [m.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(m), 5)
    def test_no_crash(self): AsyncProxy().get("x")

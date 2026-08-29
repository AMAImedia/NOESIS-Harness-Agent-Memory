import unittest
from noesis_harness.async_bind import AsyncBind

class TestAsyncBind(unittest.TestCase):
    def test_binding(self): m = AsyncBind(); self.assertEqual(m.binding("a", lambda: 1), 1)
    def test_cached(self): m = AsyncBind(); m.binding("a", lambda: 1); self.assertEqual(m.binding("a", lambda: 2), 1)
    def test_get(self): m = AsyncBind(); m.set("k", 1); self.assertEqual(m.get("k"), 1)
    def test_get_default(self): self.assertEqual(AsyncBind().get("x", 5), 5)
    def test_invalidate(self): m = AsyncBind(); m.set("k", 1); self.assertTrue(m.invalidate("k")); self.assertFalse(m.invalidate("k"))
    def test_clear(self): m = AsyncBind(); m.set("a", 1); m.set("b", 2); self.assertEqual(m.clear(), 2); self.assertEqual(len(m), 0)
    def test_len(self): m = AsyncBind(); m.set("a", 1); m.set("b", 2); self.assertEqual(len(m), 2)
    def test_deterministic(self): m = AsyncBind(); m.set("a", 1); self.assertEqual(m.get("a"), m.get("a"))
    def test_many(self): m = AsyncBind(); [m.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(m), 5)
    def test_no_crash(self): AsyncBind().get("x")

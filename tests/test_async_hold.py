import unittest
from noesis_harness.async_hold import AsyncHold

class TestAsyncHold(unittest.TestCase):
    def test_hold(self): m = AsyncHold(); self.assertEqual(m.hold("a", lambda: 1), 1)
    def test_cached(self): m = AsyncHold(); m.hold("a", lambda: 1); self.assertEqual(m.hold("a", lambda: 2), 1)
    def test_get(self): m = AsyncHold(); m.set("k", 1); self.assertEqual(m.get("k"), 1)
    def test_get_default(self): self.assertEqual(AsyncHold().get("x", 5), 5)
    def test_invalidate(self): m = AsyncHold(); m.set("k", 1); self.assertTrue(m.invalidate("k")); self.assertFalse(m.invalidate("k"))
    def test_clear(self): m = AsyncHold(); m.set("a", 1); m.set("b", 2); self.assertEqual(m.clear(), 2); self.assertEqual(len(m), 0)
    def test_len(self): m = AsyncHold(); m.set("a", 1); m.set("b", 2); self.assertEqual(len(m), 2)
    def test_deterministic(self): m = AsyncHold(); m.set("a", 1); self.assertEqual(m.get("a"), m.get("a"))
    def test_many(self): m = AsyncHold(); [m.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(m), 5)
    def test_no_crash(self): AsyncHold().get("x")

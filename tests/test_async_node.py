import unittest
from noesis_harness.async_node import AsyncNode

class TestAsyncNode(unittest.TestCase):
    def test_node(self): m = AsyncNode(); self.assertEqual(m.node("a", lambda: 1), 1)
    def test_cached(self): m = AsyncNode(); m.node("a", lambda: 1); self.assertEqual(m.node("a", lambda: 2), 1)
    def test_get(self): m = AsyncNode(); m.set("k", 1); self.assertEqual(m.get("k"), 1)
    def test_get_default(self): self.assertEqual(AsyncNode().get("x", 5), 5)
    def test_invalidate(self): m = AsyncNode(); m.set("k", 1); self.assertTrue(m.invalidate("k")); self.assertFalse(m.invalidate("k"))
    def test_clear(self): m = AsyncNode(); m.set("a", 1); m.set("b", 2); self.assertEqual(m.clear(), 2); self.assertEqual(len(m), 0)
    def test_len(self): m = AsyncNode(); m.set("a", 1); m.set("b", 2); self.assertEqual(len(m), 2)
    def test_deterministic(self): m = AsyncNode(); m.set("a", 1); self.assertEqual(m.get("a"), m.get("a"))
    def test_many(self): m = AsyncNode(); [m.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(m), 5)
    def test_no_crash(self): AsyncNode().get("x")

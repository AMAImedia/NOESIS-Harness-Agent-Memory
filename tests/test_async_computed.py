import unittest
from noesis_harness.async_computed import AsyncComputed

class TestAsyncComputed(unittest.TestCase):
    def test_register_get(self): m = AsyncComputed(); m.register("a", lambda: 1); self.assertEqual(m.get("a"), 1)
    def test_cached(self): m = AsyncComputed(); m.register("a", lambda: 1); m.get("a"); self.assertEqual(m.get("a"), 1)
    def test_missing(self): self.assertIsNone(AsyncComputed().get("x"))
    def test_invalidate(self): m = AsyncComputed(); m.register("a", lambda: 1); m.get("a"); self.assertTrue(m.invalidate("a")); self.assertIsNone(m.get("a"))
    def test_clear(self): m = AsyncComputed(); m.register("a", lambda: 1); m.get("a"); self.assertEqual(m.clear(), 1); self.assertEqual(len(m), 0)
    def test_len(self): m = AsyncComputed(); m.register("a", lambda: 1); m.get("a"); m.register("b", lambda: 2); self.assertEqual(len(m), 1)
    def test_deterministic(self): m = AsyncComputed(); m.register("a", lambda: 5); self.assertEqual(m.get("a"), m.get("a"))
    def test_many(self): m = AsyncComputed(); [m.register(f"k{i}", lambda i=i: i) for i in range(5)]; [m.get(f"k{i}") for i in range(5)]; self.assertEqual(len(m), 5)
    def test_no_crash(self): AsyncComputed().get("x")
    def test_workers(self): m = AsyncComputed(max_workers=1); m.register("a", lambda: 1); self.assertEqual(m.get("a"), 1)

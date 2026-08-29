import unittest
from noesis_harness.async_factory import AsyncFactory

class TestAsyncFactory(unittest.TestCase):
    def test_register_get(self): m = AsyncFactory(); m.register("a", lambda: 1); self.assertEqual(m.get("a"), 1)
    def test_cached(self): m = AsyncFactory(); m.register("a", lambda: 1); m.get("a"); self.assertEqual(m.get("a"), 1)
    def test_missing(self): self.assertIsNone(AsyncFactory().get("x"))
    def test_invalidate(self): m = AsyncFactory(); m.register("a", lambda: 1); m.get("a"); self.assertTrue(m.invalidate("a")); self.assertIsNone(m.get("a"))
    def test_clear(self): m = AsyncFactory(); m.register("a", lambda: 1); m.get("a"); self.assertEqual(m.clear(), 1); self.assertEqual(len(m), 0)
    def test_len(self): m = AsyncFactory(); m.register("a", lambda: 1); m.register("b", lambda: 2); m.get("a"); self.assertEqual(len(m), 1)
    def test_deterministic(self): m = AsyncFactory(); m.register("a", lambda: 5); self.assertEqual(m.get("a"), m.get("a"))
    def test_many(self): m = AsyncFactory(); [m.register(f"k{i}", lambda i=i: i) for i in range(5)]; [m.get(f"k{i}") for i in range(5)]; self.assertEqual(len(m), 5)
    def test_no_crash(self): AsyncFactory().get("x")
    def test_workers(self): m = AsyncFactory(max_workers=1); m.register("a", lambda: 1); self.assertEqual(m.get("a"), 1)

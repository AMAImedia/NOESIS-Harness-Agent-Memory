import unittest
from noesis_harness.memoize_computed import MemoComputed

class TestMemoComputed(unittest.TestCase):
    def test_register_get(self): m = MemoComputed(); m.register("a", lambda: 1); self.assertEqual(m.get("a"), 1)
    def test_cached(self): m = MemoComputed(); m.register("a", lambda: 1); m.get("a"); self.assertEqual(m.get("a"), 1)
    def test_missing(self): self.assertIsNone(MemoComputed().get("x"))
    def test_invalidate(self): m = MemoComputed(); m.register("a", lambda: 1); m.get("a"); self.assertTrue(m.invalidate("a")); self.assertIsNone(m.get("a"))
    def test_clear(self): m = MemoComputed(); m.register("a", lambda: 1); m.get("a"); self.assertEqual(m.clear(), 1); self.assertEqual(len(m), 0)
    def test_len(self): m = MemoComputed(); m.register("a", lambda: 1); m.get("a"); m.register("b", lambda: 2); self.assertEqual(len(m), 1)
    def test_contains(self): m = MemoComputed(); m.register("a", lambda: 1); self.assertIn("a", m)
    def test_deterministic(self): m = MemoComputed(); m.register("a", lambda: 5); self.assertEqual(m.get("a"), m.get("a"))
    def test_many(self): m = MemoComputed(); [m.register(f"k{i}", lambda i=i: i) for i in range(5)]; [m.get(f"k{i}") for i in range(5)]; self.assertEqual(len(m), 5)
    def test_computed_once(self):
        m = MemoComputed(); c = [0]
        m.register("a", lambda: (c.__setitem__(0, c[0] + 1), c[0])[1])
        m.get("a"); m.get("a"); self.assertEqual(c[0], 1)

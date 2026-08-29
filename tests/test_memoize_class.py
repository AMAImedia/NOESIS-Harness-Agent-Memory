import unittest
from noesis_harness.memoize_class import Memoizer

class TestMemoizeClass(unittest.TestCase):
    def test_get_or_compute(self):
        m = Memoizer(); self.assertEqual(m.get_or_compute("a", lambda: 1), 1)
    def test_cached(self):
        m = Memoizer(); m.get_or_compute("a", lambda: 1)
        self.assertEqual(m.get_or_compute("a", lambda: 99), 1)
    def test_invalidate(self):
        m = Memoizer(); m.get_or_compute("a", lambda: 1)
        self.assertTrue(m.invalidate("a")); self.assertFalse(m.invalidate("a"))
    def test_clear(self):
        m = Memoizer(); m.get_or_compute("a", lambda: 1); m.get_or_compute("b", lambda: 2)
        self.assertEqual(m.clear(), 2); self.assertEqual(len(m), 0)
    def test_len(self):
        m = Memoizer(); m.get_or_compute("a", lambda: 1); self.assertEqual(len(m), 1)
    def test_contains(self):
        m = Memoizer(); m.get_or_compute("a", lambda: 1)
        self.assertIn("a", m); self.assertNotIn("b", m)
    def test_no_mutation(self):
        m = Memoizer(); m.get_or_compute("a", lambda: 1); m.get_or_compute("a", lambda: 2)
        self.assertEqual(m.get_or_compute("a", lambda: 3), 1)
    def test_deterministic(self):
        m = Memoizer(); self.assertEqual(m.get_or_compute("a", lambda: 5), m.get_or_compute("a", lambda: 6))
    def test_many(self):
        m = Memoizer(); [m.get_or_compute(f"k{i}", lambda i=i: i) for i in range(5)]
        self.assertEqual(len(m), 5)
    def test_compute_called_once(self):
        m = Memoizer(); c = [0]
        m.get_or_compute("a", lambda: (c.__setitem__(0, c[0] + 1), c[0])[1])
        m.get_or_compute("a", lambda: 99)
        self.assertEqual(c[0], 1)

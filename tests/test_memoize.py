import unittest
from noesis_harness.memoize import memoize

class TestMemoize(unittest.TestCase):
    def test_cache(self):
        calls = []
        @memoize
        def f(x): calls.append(x); return x*2
        self.assertEqual(f(2), 4); self.assertEqual(f(2), 4); self.assertEqual(len(calls), 1)
    def test_different_args(self):
        @memoize
        def f(x): return x
        self.assertEqual(f(1), 1); self.assertEqual(f(2), 2)
    def test_kwargs(self):
        @memoize
        def f(a, b=1): return a+b
        self.assertEqual(f(1, b=2), 3); self.assertEqual(f(1, b=2), 3)
    def test_clear(self):
        @memoize
        def f(x): return x
        f(1); f.cache_clear(); self.assertEqual(f.cache_info()["size"], 0)
    def test_info(self):
        @memoize
        def f(x): return x
        f(1); f(2); self.assertEqual(f.cache_info()["size"], 2)
    def test_determinism(self):
        @memoize
        def f(x): return x*2
        a = f(3); b = f(3); self.assertEqual(a, b)
    def test_none(self):
        @memoize
        def f(x): return None
        self.assertIsNone(f(1)); self.assertIsNone(f(1))
    def test_zero(self):
        @memoize
        def f(x): return x
        self.assertEqual(f(0), 0)
    def test_preserves(self):
        @memoize
        def f(x): return x
        self.assertEqual(f.__wrapped__(5) if hasattr(f, "__wrapped__") else f(5), 5)
    def test_many(self):
        @memoize
        def f(x): return x
        for i in range(20): f(i)
        self.assertEqual(f.cache_info()["size"], 20)

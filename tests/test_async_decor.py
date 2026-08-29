import unittest
from noesis_harness.async_decor import AsyncDecor

class TestAsyncDecor(unittest.TestCase):
    def test_decor(self):
        m = AsyncDecor()
        @m.decor
        def f(x): return x * 2
        self.assertEqual(f(5), 10)
    def test_cached(self):
        m = AsyncDecor(); c = [0]
        @m.decor
        def f(x):
            c[0] += 1; return x * 2
        f(5); f(5); self.assertEqual(c[0], 1)
    def test_len(self):
        m = AsyncDecor()
        @m.decor
        def f(x): return x
        f(1); f(2); self.assertEqual(len(m), 2)
    def test_invalidate(self):
        m = AsyncDecor()
        @m.decor
        def f(x): return x
        f(5); self.assertTrue(m.invalidate(((5,), ()))); self.assertEqual(len(m), 0)
    def test_clear(self):
        m = AsyncDecor()
        @m.decor
        def f(x): return x
        f(1); f(2); self.assertEqual(m.clear(), 2)
    def test_deterministic(self):
        m = AsyncDecor()
        @m.decor
        def f(x): return x
        self.assertEqual(f(1), f(1))
    def test_many(self):
        m = AsyncDecor()
        @m.decor
        def f(x): return x
        for i in range(5): f(i)
        self.assertEqual(len(m), 5)
    def test_no_crash(self):
        m = AsyncDecor()
        @m.decor
        def f(x): return x
        f(1)
    def test_workers(self):
        m = AsyncDecor(max_workers=1)
        @m.decor
        def f(x): return x
        self.assertEqual(f(1), 1)
    def test_kwargs(self):
        m = AsyncDecor()
        @m.decor
        def f(x, y=0): return x + y
        self.assertEqual(f(1, y=2), 3)

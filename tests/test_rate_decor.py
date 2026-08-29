import time, unittest
from noesis_harness.rate_decor import RateDecor

class TestRateDecor(unittest.TestCase):
    def test_decor(self):
        m = RateDecor(10)
        @m.decor
        def f(x): return x * 2
        self.assertEqual(f(5), 10)
    def test_cached(self):
        m = RateDecor(10); c = [0]
        @m.decor
        def f(x):
            c[0] += 1; return x * 2
        f(5); f(5); self.assertEqual(c[0], 1)
    def test_ttl(self):
        m = RateDecor(0.01)
        @m.decor
        def f(x): return x
        f(5); time.sleep(0.02); c = [0]
        @m.decor
        def g(x):
            c[0] += 1; return x
        g(5); self.assertEqual(c[0], 1)
    def test_len(self):
        m = RateDecor(10)
        @m.decor
        def f(x): return x
        f(1); f(2); self.assertEqual(len(m), 2)
    def test_invalidate(self):
        m = RateDecor(10)
        @m.decor
        def f(x): return x
        f(5); self.assertTrue(m.invalidate(((5,), ()))); self.assertEqual(len(m), 0)
    def test_clear(self):
        m = RateDecor(10)
        @m.decor
        def f(x): return x
        f(1); f(2); self.assertEqual(m.clear(), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RateDecor(0)
    def test_deterministic(self):
        m = RateDecor(10)
        @m.decor
        def f(x): return x
        self.assertEqual(f(1), f(1))
    def test_many(self):
        m = RateDecor(10)
        @m.decor
        def f(x): return x
        for i in range(5): f(i)
        self.assertEqual(len(m), 5)
    def test_kwargs(self):
        m = RateDecor(10)
        @m.decor
        def f(x, y=0): return x + y
        self.assertEqual(f(1, y=2), 3)

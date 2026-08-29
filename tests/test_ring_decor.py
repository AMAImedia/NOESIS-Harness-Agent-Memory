import unittest
from noesis_harness.ring_decor import RingDecor

class TestRingDecor(unittest.TestCase):
    def test_decor(self):
        m = RingDecor(5)
        @m.decor
        def f(x): return x * 2
        self.assertEqual(f(5), 10)
    def test_cached(self):
        m = RingDecor(5); c = [0]
        @m.decor
        def f(x):
            c[0] += 1; return x * 2
        f(5); f(5); self.assertEqual(c[0], 1)
    def test_overflow(self):
        m = RingDecor(2)
        @m.decor
        def f(x): return x
        f(1); f(2); f(3); self.assertEqual(len(m), 2)
    def test_len(self):
        m = RingDecor(5)
        @m.decor
        def f(x): return x
        f(1); f(2); self.assertEqual(len(m), 2)
    def test_invalidate(self):
        m = RingDecor(5)
        @m.decor
        def f(x): return x
        f(5); self.assertTrue(m.invalidate(((5,), ()))); self.assertEqual(len(m), 0)
    def test_clear(self):
        m = RingDecor(5)
        @m.decor
        def f(x): return x
        f(1); f(2); self.assertEqual(m.clear(), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingDecor(0)
    def test_deterministic(self):
        m = RingDecor(5)
        @m.decor
        def f(x): return x
        self.assertEqual(f(1), f(1))
    def test_many(self):
        m = RingDecor(10)
        @m.decor
        def f(x): return x
        for i in range(10): f(i)
        self.assertTrue(m.full())
    def test_kwargs(self):
        m = RingDecor(5)
        @m.decor
        def f(x, y=0): return x + y
        self.assertEqual(f(1, y=2), 3)

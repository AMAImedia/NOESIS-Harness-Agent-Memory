import unittest
from noesis_harness.decorator_util import wrap, once

class TestDecoratorUtil(unittest.TestCase):
    def test_wrap(self):
        log = []; fn = wrap(lambda: 1, before=lambda: log.append("b"), after=lambda: log.append("a"))
        self.assertEqual(fn(), 1); self.assertEqual(log, ["b", "a"])
    def test_before_only(self):
        log = []; fn = wrap(lambda: 2, before=lambda: log.append("x"))
        fn(); self.assertEqual(log, ["x"])
    def test_after_only(self):
        log = []; fn = wrap(lambda: 3, after=lambda: log.append("y"))
        fn(); self.assertEqual(log, ["y"])
    def test_no_hooks(self): self.assertEqual(wrap(lambda: 5)(), 5)
    def test_once(self):
        c = [0]; fn = once(lambda: (c.__setitem__(0, c[0] + 1), c[0])[1])
        fn(); fn(); fn(); self.assertEqual(c[0], 1)
    def test_once_result(self):
        fn = once(lambda: 42); self.assertEqual(fn(), fn())
    def test_args(self): fn = wrap(lambda x, y: x + y); self.assertEqual(fn(1, 2), 3)
    def test_kwargs(self): fn = wrap(lambda x=0: x); self.assertEqual(fn(x=5), 5)
    def test_deterministic(self): fn = once(lambda: 10); self.assertEqual(fn(), fn())
    def test_many(self):
        for _ in range(5): fn = once(lambda: 1); self.assertEqual(fn(), 1)

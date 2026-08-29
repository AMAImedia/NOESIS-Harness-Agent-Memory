import unittest
from noesis_harness.lazy_property import lazy_property

class Obj:
    def __init__(self, val): self.val = val
    @lazy_property
    def computed(self): return self.val * 2

class TestLazyProperty(unittest.TestCase):
    def test_basic(self): self.assertEqual(Obj(5).computed, 10)
    def test_cached(self): o = Obj(3); self.assertEqual(o.computed, o.computed)
    def test_different(self): self.assertEqual(Obj(1).computed, 2); self.assertEqual(Obj(2).computed, 4)
    def test_class(self): self.assertIsNotNone(Obj(0).computed)
    def test_access_class(self): self.assertIsNone(type.__dict__.get("computed"))
    def test_deterministic(self): self.assertEqual(Obj(7).computed, Obj(7).computed)
    def test_many(self):
        for i in range(5): self.assertEqual(Obj(i).computed, i * 2)
    def test_no_crash(self): Obj(0).computed
    def test_zero(self): self.assertEqual(Obj(0).computed, 0)
    def test_negative(self): self.assertEqual(Obj(-1).computed, -2)

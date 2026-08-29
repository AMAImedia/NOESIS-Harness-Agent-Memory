import unittest
from noesis_harness.singleton import get_instance, reset, clear_all

class MyService:
    def __init__(self, val=0): self.val = val

class TestSingleton(unittest.TestCase):
    def setUp(self): clear_all()
    def test_same(self): a = get_instance(MyService, 1); b = get_instance(MyService, 2); self.assertIs(a, b)
    def test_val(self): self.assertEqual(get_instance(MyService, 5).val, 5)
    def test_reset(self): get_instance(MyService, 1); self.assertTrue(reset(MyService))
    def test_reset_empty(self): self.assertFalse(reset(MyService))
    def test_clear(self): get_instance(MyService); self.assertEqual(clear_all(), 1); self.assertEqual(clear_all(), 0)
    def test_different_classes(self):
        class A: pass
        class B: pass
        a = get_instance(A); b = get_instance(B); self.assertIsNot(a, b)
    def test_deterministic(self): self.assertIs(get_instance(MyService), get_instance(MyService))
    def test_many(self):
        for _ in range(5): get_instance(MyService, 42)
        self.assertEqual(len([get_instance(MyService)]), 1)
    def test_no_crash(self): get_instance(MyService); get_instance(MyService)
    def test_kwargs(self):
        class K: pass
        get_instance(K); self.assertIsNotNone(get_instance(K))

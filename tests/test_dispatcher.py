import unittest
from noesis_harness.dispatcher import Dispatcher

class TestDispatcher(unittest.TestCase):
    def test_dispatch(self): d = Dispatcher(); d.register("add", lambda a, b: a+b); self.assertEqual(d.dispatch("add", 1, 2), 3)
    def test_names(self): d = Dispatcher(); d.register("a", lambda: 1); self.assertEqual(d.names(), ["a"])
    def test_unknown(self):
        with self.assertRaises(KeyError): Dispatcher().dispatch("x")
    def test_empty_name(self):
        with self.assertRaises(ValueError): Dispatcher().register("", lambda: None)
    def test_multiple(self): d = Dispatcher(); d.register("a", lambda: 1); d.register("b", lambda: 2); self.assertEqual(d.dispatch("b"), 2)
    def test_kwargs(self): d = Dispatcher(); d.register("f", lambda x, y=0: x+y); self.assertEqual(d.dispatch("f", 1, y=2), 3)
    def test_no_mutation(self): d = Dispatcher(); d.register("f", lambda: 1); d.dispatch("f"); self.assertEqual(d.names(), ["f"])
    def test_determinism(self): d = Dispatcher(); d.register("f", lambda: 1); self.assertEqual(d.dispatch("f"), d.dispatch("f"))
    def test_overwrite(self): d = Dispatcher(); d.register("f", lambda: 1); d.register("f", lambda: 2); self.assertEqual(d.dispatch("f"), 2)
    def test_many(self):
        d = Dispatcher()
        for i in range(5): d.register(f"f{i}", lambda i=i: i)
        self.assertEqual(len(d.names()), 5)

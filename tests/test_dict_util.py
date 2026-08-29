import unittest
from noesis_harness.dict_util import get_nested, set_nested, pick, omit, invert

class TestDictUtil(unittest.TestCase):
    def test_get_nested(self): self.assertEqual(get_nested({"a": {"b": 1}}, "a.b"), 1)
    def test_get_missing(self): self.assertEqual(get_nested({}, "x.y", "d"), "d")
    def test_set_nested(self):
        d = {}; set_nested(d, "a.b", 1); self.assertEqual(d, {"a": {"b": 1}})
    def test_pick(self): self.assertEqual(pick({"a": 1, "b": 2}, ["a"]), {"a": 1})
    def test_omit(self): self.assertEqual(omit({"a": 1, "b": 2}, ["a"]), {"b": 2})
    def test_invert(self): self.assertEqual(invert({"a": 1, "b": 2}), {1: "a", 2: "b"})
    def test_deep(self): d = {}; set_nested(d, "x.y.z", 9); self.assertEqual(get_nested(d, "x.y.z"), 9)
    def test_no_mutate(self): d = {"a": 1}; pick(d, ["a"]); self.assertEqual(d, {"a": 1})
    def test_determinism(self): self.assertEqual(get_nested({"a": 1}, "a"), get_nested({"a": 1}, "a"))
    def test_many(self):
        d = {}
        for i in range(5): set_nested(d, f"a{i}.b{i}", i)
        self.assertEqual(len(d), 5)

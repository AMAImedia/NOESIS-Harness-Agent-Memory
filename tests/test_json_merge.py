import unittest
from noesis_harness.json_merge import merge

class TestMerge(unittest.TestCase):
    def test_flat(self): self.assertEqual(merge({"a":1},{"a":2}),{"a":2})
    def test_add(self): self.assertEqual(merge({"a":1},{"b":2}),{"a":1,"b":2})
    def test_nested(self): self.assertEqual(merge({"a":{"x":1}},{"a":{"y":2}}),{"a":{"x":1,"y":2}})
    def test_override(self): self.assertEqual(merge({"a":{"x":1}},{"a":2}),{"a":2})
    def test_empty(self): self.assertEqual(merge({},{"a":1}),{"a":1})
    def test_no_mutate(self): a={"x":1}; merge(a,{"y":2}); self.assertEqual(a,{"x":1})
    def test_deep(self): self.assertEqual(merge({"a":{"b":{"c":1}}},{"a":{"b":{"d":2}}}),{"a":{"b":{"c":1,"d":2}}})
    def test_determinism(self): self.assertEqual(merge({"a":1},{"b":2}),merge({"a":1},{"b":2}))
    def test_both_empty(self): self.assertEqual(merge({},{}) ,{})
    def test_new_key(self): self.assertEqual(merge({"a":1},{"b":{"c":3}}),{"a":1,"b":{"c":3}})

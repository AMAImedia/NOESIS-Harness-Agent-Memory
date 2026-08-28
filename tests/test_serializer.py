import unittest
from noesis_harness.serializer import to_json, from_json

class TestSerializer(unittest.TestCase):
    def test_roundtrip(self):
        d = {"a": 1, "b": [1, 2]}; self.assertEqual(from_json(to_json(d)), d)
    def test_set(self): self.assertEqual(from_json(to_json({"s": {1, 2}})), {"s": [1, 2]})
    def test_sorted_keys(self): self.assertEqual(to_json({"b": 1, "a": 2}), '{"a": 2, "b": 1}')
    def test_scalar(self): self.assertEqual(from_json(to_json(5)), 5)
    def test_list(self): self.assertEqual(from_json(to_json([1, 2, 3])), [1, 2, 3])
    def test_str(self): self.assertEqual(from_json(to_json("hi")), "hi")
    def test_object(self):
        class O: pass
        o = O(); o.x = 1
        self.assertEqual(from_json(to_json(o)), {"x": 1})
    def test_empty(self): self.assertEqual(from_json(to_json({})), {})
    def test_nested(self): self.assertEqual(from_json(to_json({"a": {"b": {"c": 3}}})), {"a": {"b": {"c": 3}}})
    def test_determinism(self): self.assertEqual(to_json({"a": 1}), to_json({"a": 1}))

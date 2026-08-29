import unittest
from noesis_harness.json_schema import validate

class TestJsonSchema(unittest.TestCase):
    def test_valid(self): self.assertEqual(validate("hi", {"type": "string"}), [])
    def test_invalid(self): self.assertEqual(len(validate(1, {"type": "string"})), 1)
    def test_integer(self): self.assertEqual(validate(5, {"type": "integer"}), [])
    def test_number(self): self.assertEqual(validate(5.5, {"type": "number"}), [])
    def test_boolean(self): self.assertEqual(validate(True, {"type": "boolean"}), [])
    def test_array(self): self.assertEqual(validate([1, 2], {"type": "array"}), [])
    def test_object(self): self.assertEqual(validate({"a": 1}, {"type": "object"}), [])
    def test_required(self): self.assertEqual(len(validate({}, {"type": "object", "required": ["a"]})), 1)
    def test_enum(self): self.assertEqual(validate("a", {"enum": ["a", "b"]}), [])
    def test_enum_fail(self): self.assertEqual(len(validate("c", {"enum": ["a", "b"]})), 1)
    def test_min(self): self.assertEqual(validate(5, {"minimum": 0}), [])
    def test_min_fail(self): self.assertEqual(len(validate(-1, {"minimum": 0})), 1)
    def test_max(self): self.assertEqual(validate(5, {"maximum": 10}), [])
    def test_max_fail(self): self.assertEqual(len(validate(11, {"maximum": 10})), 1)
    def test_minlength(self): self.assertEqual(validate("hi", {"minLength": 1}), [])
    def test_minlength_fail(self): self.assertEqual(len(validate("", {"minLength": 1})), 1)
    def test_nested(self):
        s = {"type": "object", "properties": {"x": {"type": "integer"}}}
        self.assertEqual(validate({"x": "bad"}, s), ["x: expected integer"])
    def test_array_items(self):
        s = {"type": "array", "items": {"type": "string"}}
        self.assertEqual(validate(["a", "b"], s), [])
    def test_array_items_fail(self):
        s = {"type": "array", "items": {"type": "string"}}
        self.assertEqual(len(validate(["a", 1], s)), 1)
    def test_deterministic(self): self.assertEqual(validate("x", {"type": "string"}), validate("x", {"type": "string"}))

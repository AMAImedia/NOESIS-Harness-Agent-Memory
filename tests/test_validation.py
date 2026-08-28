import unittest
from noesis_harness.validation import is_nonempty_str, is_positive_int, validate

class TestValidation(unittest.TestCase):
    def test_nonempty(self): self.assertTrue(is_nonempty_str("a")); self.assertFalse(is_nonempty_str("")); self.assertFalse(is_nonempty_str("   "))
    def test_positive_int(self): self.assertTrue(is_positive_int(1)); self.assertFalse(is_positive_int(0)); self.assertFalse(is_positive_int(-1))
    def test_validate_ok(self): self.assertEqual(validate({"a": "hi"}, {"a": is_nonempty_str}), [])
    def test_validate_fail(self): self.assertEqual(validate({"a": ""}, {"a": is_nonempty_str}), ["a"])
    def test_missing_key(self): self.assertEqual(validate({}, {"a": is_nonempty_str}), ["a"])
    def test_multiple(self): self.assertEqual(set(validate({"a": "", "b": 0}, {"a": is_nonempty_str, "b": is_positive_int})), {"a", "b"})
    def test_empty_rules(self): self.assertEqual(validate({"a": 1}, {}), [])
    def test_determinism(self): self.assertEqual(validate({"a": "hi"}, {"a": is_nonempty_str}), validate({"a": "hi"}, {"a": is_nonempty_str}))
    def test_non_str(self): self.assertFalse(is_nonempty_str(123))
    def test_non_int(self): self.assertFalse(is_positive_int("1"))

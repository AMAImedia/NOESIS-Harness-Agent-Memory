import unittest
from noesis_harness.enum_util import values, is_valid, names

S = {"A": "a", "B": "b"}
class TestEnumUtil(unittest.TestCase):
    def test_values(self): self.assertEqual(set(values(S)), {"a", "b"})
    def test_names(self): self.assertEqual(set(names(S)), {"A", "B"})
    def test_valid(self): self.assertTrue(is_valid(S, "a")); self.assertFalse(is_valid(S, "z"))
    def test_empty(self): self.assertEqual(values({}), [])
    def test_no_dup(self): self.assertEqual(len(values({"A": "a", "B": "a"})), 2)
    def test_determinism(self): self.assertEqual(values(S), values(S))
    def test_invalid_type(self): self.assertFalse(is_valid(S, "A"))
    def test_many(self): m = {f"K{i}": f"v{i}" for i in range(5)}; self.assertEqual(len(values(m)), 5)
    def test_missing(self): self.assertFalse(is_valid(S, "x"))
    def test_case(self): self.assertFalse(is_valid(S, "A"))

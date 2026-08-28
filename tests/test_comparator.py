import unittest
from noesis_harness.comparator import equals

class TestComparator(unittest.TestCase):
    def test_equal(self): self.assertTrue(equals({"a": 1}, {"a": 1}))
    def test_diff(self): self.assertFalse(equals({"a": 1}, {"a": 2}))
    def test_nested(self): self.assertTrue(equals({"a": {"b": [1, 2]}}, {"a": {"b": [1, 2]}}))
    def test_type(self): self.assertFalse(equals(1, "1"))
    def test_set(self): self.assertTrue(equals({1, 2}, {2, 1}))
    def test_list(self): self.assertTrue(equals([1, 2, 3], [1, 2, 3])); self.assertFalse(equals([1, 2], [2, 1]))
    def test_tuple(self): self.assertTrue(equals((1, 2), (1, 2)))
    def test_scalar(self): self.assertTrue(equals(5, 5)); self.assertFalse(equals(5, 6))
    def test_missing_key(self): self.assertFalse(equals({"a": 1}, {"a": 1, "b": 2}))
    def test_determinism(self): self.assertEqual(equals([1, 2], [1, 2]), equals([1, 2], [1, 2]))

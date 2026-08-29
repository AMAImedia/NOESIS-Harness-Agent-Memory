import unittest
from noesis_harness.validate_util import required, in_range, matches, validate_all

class TestValidateUtil(unittest.TestCase):
    def test_required_ok(self): self.assertEqual(required("hello"), [])
    def test_required_none(self): self.assertEqual(len(required(None)), 1)
    def test_required_empty(self): self.assertEqual(len(required("")), 1)
    def test_in_range_ok(self): self.assertEqual(in_range(5, 0, 10), [])
    def test_in_range_fail(self): self.assertEqual(len(in_range(11, 0, 10)), 1)
    def test_matches_ok(self): self.assertEqual(matches("abc123", r"^[a-z0-9]+$"), [])
    def test_matches_fail(self): self.assertEqual(len(matches("abc!", r"^[a-z0-9]+$")), 1)
    def test_validate_all(self):
        checks = [lambda v: required(v), lambda v: in_range(v, 0, 10)]
        self.assertEqual(validate_all(5, checks), [])
    def test_validate_all_fail(self):
        checks = [lambda v: required(v), lambda v: in_range(v, 0, 10)]
        self.assertEqual(len(validate_all(11, checks)), 1)
    def test_deterministic(self): self.assertEqual(required("x"), required("x"))

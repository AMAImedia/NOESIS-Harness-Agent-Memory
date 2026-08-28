import unittest
from noesis_harness.option import Some, NONE, some, none

class TestOption(unittest.TestCase):
    def test_some(self): s = some(1); self.assertTrue(s.is_some()); self.assertEqual(s.unwrap(), 1)
    def test_none(self): self.assertTrue(none().is_none())
    def test_unwrap_or_some(self): self.assertEqual(some(1).unwrap_or(2), 1)
    def test_unwrap_or_none(self): self.assertEqual(none().unwrap_or(2), 2)
    def test_none_singleton(self): self.assertIs(none(), NONE)
    def test_some_is_not_none(self): self.assertFalse(some(1).is_none())
    def test_none_unwrap_raises(self):
        with self.assertRaises(ValueError): none().unwrap()
    def test_determinism(self): self.assertEqual(some(1).unwrap(), some(1).unwrap())
    def test_none_value(self): self.assertIsNone(some(None).unwrap())
    def test_some_value(self): self.assertEqual(Some(5).value, 5)

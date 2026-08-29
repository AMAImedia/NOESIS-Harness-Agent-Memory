import unittest
from noesis_harness.base24_util import encode, decode

class TestBase24(unittest.TestCase):
    def test_zero(self): self.assertEqual(encode(0), "A")
    def test_one(self): self.assertEqual(encode(1), "B")
    def test_roundtrip(self):
        for i in range(100): self.assertEqual(decode(encode(i)), i)
    def test_invalid(self):
        with self.assertRaises(ValueError): encode(-1)
    def test_deterministic(self): self.assertEqual(encode(42), encode(42))
    def test_string(self): self.assertIsInstance(encode(1), str)
    def test_many(self):
        for i in range(200): self.assertEqual(decode(encode(i)), i)
    def test_no_crash(self): encode(99999)
    def test_special_chars(self): self.assertNotIn("O", encode(1000)); self.assertNotIn("I", encode(1000))
    def test_deterministic_decode(self): self.assertEqual(decode("ABC"), decode("ABC"))

import unittest
from noesis_harness.hex_util import to_hex, from_hex, to_hex_str, from_hex_str

class TestHex(unittest.TestCase):
    def test_roundtrip(self): self.assertEqual(from_hex(to_hex(b"abc")), b"abc")
    def test_str(self): self.assertEqual(from_hex_str(to_hex_str("hi")), "hi")
    def test_known(self): self.assertEqual(to_hex(b"ABC"), "414243")
    def test_empty(self): self.assertEqual(to_hex(b""), "")
    def test_unicode(self): self.assertEqual(from_hex_str(to_hex_str("привет")), "привет")
    def test_determinism(self): self.assertEqual(to_hex(b"x"), to_hex(b"x"))
    def test_lower(self): self.assertEqual(to_hex(b"A"), "41")
    def test_long(self): self.assertEqual(from_hex(to_hex(b"z" * 50)), b"z" * 50)
    def test_known2(self): self.assertEqual(from_hex("ff"), b"\xff")
    def test_no_crash(self): to_hex(b"symbols !@#$%")

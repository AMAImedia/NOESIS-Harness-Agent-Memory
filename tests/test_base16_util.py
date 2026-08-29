import unittest
from noesis_harness.base16_util import encode, decode

class TestBase16(unittest.TestCase):
    def test_roundtrip(self): self.assertEqual(decode(encode(b"hello")), b"hello")
    def test_empty(self): self.assertEqual(encode(b""), "")
    def test_known(self): self.assertEqual(encode(b"ABC"), "414243")
    def test_unicode(self): self.assertEqual(decode(encode("привет".encode())), "привет".encode())
    def test_deterministic(self): self.assertEqual(encode(b"abc"), encode(b"abc"))
    def test_long(self): self.assertEqual(decode(encode(b"a"*100)), b"a"*100)
    def test_special(self): self.assertEqual(decode("ff"), b"\xff")
    def test_no_crash(self): encode(b"data with spaces and symbols !@#")
    def test_many(self): self.assertEqual(len(encode(b"test")), 8)
    def test_upper(self): self.assertEqual(encode(b"\xff"), "ff")

import unittest
from noesis_harness.base64_util import encode, decode, encode_str, decode_str

class TestBase64(unittest.TestCase):
    def test_roundtrip(self): self.assertEqual(decode(encode(b"hello")), b"hello")
    def test_str(self): self.assertEqual(decode_str(encode_str("привет")), "привет")
    def test_known(self): self.assertEqual(encode(b"hello"), "aGVsbG8=")
    def test_empty(self): self.assertEqual(encode(b""), "")
    def test_unicode_bytes(self): self.assertEqual(decode(encode("é".encode("utf-8"))), "é".encode("utf-8"))
    def test_determinism(self): self.assertEqual(encode(b"x"), encode(b"x"))
    def test_long(self): self.assertEqual(decode(encode(b"a" * 100)), b"a" * 100)
    def test_known2(self): self.assertEqual(decode("Zm9v"), b"foo")
    def test_roundtrip_str(self): self.assertEqual(encode_str("abc"), encode(b"abc"))
    def test_no_crash(self): encode(b"data with spaces and symbols !@#")

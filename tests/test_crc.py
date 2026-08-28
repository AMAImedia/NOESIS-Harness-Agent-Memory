import unittest
from noesis_harness.crc import crc32, crc_hex, crc_str

class TestCRC(unittest.TestCase):
    def test_bytes(self): self.assertEqual(crc32(b"abc"), 0x352441C2)
    def test_hex_len(self): self.assertEqual(len(crc_hex(b"abc")), 8)
    def test_str(self): self.assertEqual(crc_str("abc"), crc_hex("abc".encode("utf-8")))
    def test_empty(self): self.assertEqual(crc32(b""), 0)
    def test_deterministic(self): self.assertEqual(crc32(b"hello"), crc32(b"hello"))
    def test_diff(self): self.assertNotEqual(crc32(b"abc"), crc32(b"abd"))
    def test_int_range(self): self.assertTrue(0 <= crc32(b"x") <= 0xFFFFFFFF)
    def test_hex_format(self): self.assertTrue(all(c in "0123456789abcdef" for c in crc_hex(b"x")))
    def test_unicode(self): self.assertEqual(crc_str("привет"), crc_hex("привет".encode("utf-8")))
    def test_long(self): self.assertEqual(crc32(b"a" * 1000), crc32(b"a" * 1000))

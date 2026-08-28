import unittest
from noesis_harness.compress import compress, decompress, ratio

class TestCompress(unittest.TestCase):
    def test_roundtrip(self): d = b"hello world"*10; self.assertEqual(decompress(compress(d)), d)
    def test_empty(self): self.assertEqual(decompress(compress(b"")), b"")
    def test_ratio(self): self.assertLess(ratio(b"a"*100), 1.0)
    def test_ratio_empty(self): self.assertEqual(ratio(b""), 0.0)
    def test_determinism(self): d = b"abc"; self.assertEqual(compress(d), compress(d))
    def test_bytes(self): self.assertIsInstance(compress(b"x"), bytes)
    def test_unicode_bytes(self): d = "привет".encode("utf-8"); self.assertEqual(decompress(compress(d)), d)
    def test_large(self): d = b"x"*10000; self.assertEqual(decompress(compress(d)), d)
    def test_no_mutation(self): d = b"abc"; c = compress(d); self.assertEqual(d, b"abc")
    def test_ratio_range(self): self.assertGreaterEqual(ratio(b"abcdefgh"), 0)

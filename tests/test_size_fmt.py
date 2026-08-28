import unittest
from noesis_harness.size_fmt import format_bytes

class TestSizeFmt(unittest.TestCase):
    def test_bytes(self): self.assertEqual(format_bytes(512), "512 B")
    def test_kb(self): self.assertEqual(format_bytes(1024), "1.00 KB")
    def test_2kb(self): self.assertEqual(format_bytes(2048), "2.00 KB")
    def test_mb(self): self.assertTrue(format_bytes(1024 * 1024).startswith("1.00 MB"))
    def test_zero(self): self.assertEqual(format_bytes(0), "0 B")
    def test_invalid(self):
        with self.assertRaises(ValueError): format_bytes(-1)
    def test_gb(self): self.assertTrue(format_bytes(1024 ** 3).startswith("1.00 GB"))
    def test_1_5mb(self): self.assertEqual(format_bytes(int(1.5 * 1024 * 1024)), "1.50 MB")
    def test_determinism(self): self.assertEqual(format_bytes(9999), format_bytes(9999))
    def test_odd(self): self.assertTrue(format_bytes(1536).startswith("1.50"))

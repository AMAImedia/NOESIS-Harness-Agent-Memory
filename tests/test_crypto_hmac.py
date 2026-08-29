import unittest
from noesis_harness.crypto_hmac import sign, verify

class TestHmac(unittest.TestCase):
    def test_sign(self): self.assertEqual(len(sign(b"key", b"data")), 64)
    def test_verify_ok(self): sig = sign(b"key", b"data"); self.assertTrue(verify(b"key", b"data", sig))
    def test_verify_bad(self): self.assertFalse(verify(b"key", b"data", "0"*64))
    def test_diff_key(self): sig = sign(b"key1", b"data"); self.assertFalse(verify(b"key2", b"data", sig))
    def test_diff_data(self): sig = sign(b"key", b"data1"); self.assertFalse(verify(b"key", b"data2", sig))
    def test_deterministic(self): self.assertEqual(sign(b"k", b"d"), sign(b"k", b"d"))
    def test_empty(self): self.assertEqual(len(sign(b"", b"")), 64)
    def test_long_key(self): self.assertEqual(len(sign(b"k"*1000, b"d")), 64)
    def test_hex(self):
        s = sign(b"k", b"d"); self.assertTrue(all(c in "0123456789abcdef" for c in s))
    def test_many(self):
        for i in range(5): self.assertTrue(verify(b"k", str(i).encode(), sign(b"k", str(i).encode())))

import unittest
from noesis_harness.url_encode import encode, decode, encode_plus

class TestUrl(unittest.TestCase):
    def test_roundtrip(self): self.assertEqual(decode(encode("a b/c")), "a b/c")
    def test_plus(self): self.assertEqual(encode_plus("a b"), "a+b")
    def test_slash(self): self.assertEqual(encode("a/b"), "a%2Fb")
    def test_empty(self): self.assertEqual(encode(""), "")
    def test_unicode(self): self.assertEqual(decode(encode("привет")), "привет")
    def test_no_mutate(self): s="x y"; encode(s); self.assertEqual(s,"x y")
    def test_determinism(self): self.assertEqual(encode("hello"), encode("hello"))
    def test_decode_plus(self): self.assertEqual(decode("a+b"), "a+b")
    def test_special(self): self.assertEqual(decode(encode("!@#")), "!@#")
    def test_many(self): self.assertEqual(decode(encode("a"*50)), "a"*50)

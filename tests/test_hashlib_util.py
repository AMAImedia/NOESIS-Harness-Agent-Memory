import os, tempfile, unittest
from noesis_harness.hashlib_util import sha256, sha1, md5, hash_file

class TestHash(unittest.TestCase):
    def test_sha256(self): self.assertEqual(sha256(b"hello"), "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824")
    def test_sha1(self): self.assertEqual(sha1(b"abc"), "a9993e364706816aba3e25717850c26c9cd0d89d")
    def test_md5(self): self.assertEqual(md5(b"abc"), "900150983cd24fb0d6963f7d28e17f72")
    def test_empty(self): self.assertEqual(sha256(b""), "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
    def test_deterministic(self): self.assertEqual(sha256(b"x"), sha256(b"x"))
    def test_diff(self): self.assertNotEqual(sha256(b"a"), sha256(b"b"))
    def test_file(self):
        tmp = tempfile.mkdtemp(); p = os.path.join(tmp, "f.bin")
        open(p, "wb").write(b"data"); self.assertEqual(hash_file(p), sha256(b"data"))
    def test_long(self): self.assertEqual(len(sha256(b"a"*1000)), 64)
    def test_many(self):
        for i in range(5): self.assertEqual(len(sha256(str(i).encode())), 64)
    def test_hex(self):
        h = sha256(b"test"); self.assertTrue(all(c in "0123456789abcdef" for c in h))

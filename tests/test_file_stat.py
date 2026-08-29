import os, tempfile, time, unittest
from noesis_harness.file_stat import file_size, is_file, is_dir, mtime, age_seconds

class TestFileStat(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.p = os.path.join(self.tmp, "f.txt")
        open(self.p, "w").write("hello")
    def test_size(self): self.assertEqual(file_size(self.p), 5)
    def test_is_file(self): self.assertTrue(is_file(self.p))
    def test_is_dir(self): self.assertTrue(is_dir(self.tmp))
    def test_mtime(self): self.assertGreater(mtime(self.p), 0)
    def test_age(self): self.assertGreaterEqual(age_seconds(self.p), 0)
    def test_not_file(self): self.assertFalse(is_file("/no/such/file"))
    def test_not_dir(self): self.assertFalse(is_dir("/no/such/dir"))
    def test_empty(self):
        p = os.path.join(self.tmp, "e.txt"); open(p, "w").write("")
        self.assertEqual(file_size(p), 0)
    def test_deterministic(self): self.assertEqual(file_size(self.p), file_size(self.p))
    def test_many(self):
        for i in range(5):
            p = os.path.join(self.tmp, f"f{i}.txt"); open(p, "w").write(str(i))
            self.assertEqual(file_size(p), len(str(i)))

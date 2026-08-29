import os, tempfile, unittest
from noesis_harness.dir_util import count_files, count_dirs, list_files, ensure_dir, is_empty

class TestDirUtil(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        open(os.path.join(self.tmp, "a.txt"), "w").write("x")
        open(os.path.join(self.tmp, "b.txt"), "w").write("x")
        os.makedirs(os.path.join(self.tmp, "sub"))
    def test_count_files(self): self.assertEqual(count_files(self.tmp), 2)
    def test_count_dirs(self): self.assertEqual(count_dirs(self.tmp), 1)
    def test_list_files(self): self.assertEqual(list_files(self.tmp), ["a.txt", "b.txt"])
    def test_ensure_dir(self):
        p = os.path.join(self.tmp, "new", "nested"); ensure_dir(p); self.assertTrue(os.path.isdir(p))
    def test_is_empty(self): self.assertFalse(is_empty(self.tmp))
    def test_empty_dir(self):
        p = tempfile.mkdtemp(); self.assertTrue(is_empty(p))
    def test_no_mutation(self): list_files(self.tmp); self.assertEqual(count_files(self.tmp), 2)
    def test_deterministic(self): self.assertEqual(list_files(self.tmp), list_files(self.tmp))
    def test_sorted(self): self.assertEqual(list_files(self.tmp), sorted(list_files(self.tmp)))
    def test_many(self):
        for i in range(5): open(os.path.join(self.tmp, f"f{i}.txt"), "w").write(str(i))
        self.assertEqual(count_files(self.tmp), 7)

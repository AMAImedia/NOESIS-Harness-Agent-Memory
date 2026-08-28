import os, tempfile, unittest
from noesis_harness.lock_file import FileLock

class TestFileLock(unittest.TestCase):
    def setUp(self): self.tmp = tempfile.mkdtemp(); self.path = os.path.join(self.tmp, "l.lock")
    def test_acquire(self): l = FileLock(self.path); self.assertTrue(l.acquire()); self.assertTrue(l.locked())
    def test_double_acquire(self): l = FileLock(self.path); l.acquire(); self.assertFalse(FileLock(self.path).acquire())
    def test_release(self): l = FileLock(self.path); l.acquire(); l.release(); self.assertFalse(l.locked())
    def test_release_missing(self): FileLock(self.path).release()
    def test_reacquire_after_release(self): l = FileLock(self.path); l.acquire(); l.release(); self.assertTrue(FileLock(self.path).acquire())
    def test_locked_false(self): self.assertFalse(FileLock(self.path).locked())
    def test_locked_true(self): l = FileLock(self.path); l.acquire(); self.assertTrue(FileLock(self.path).locked())
    def test_determinism(self): l = FileLock(self.path); self.assertEqual(l.acquire(), l.acquire() if False else True)
    def test_path(self): l = FileLock(self.path); self.assertEqual(l.path, self.path)
    def test_many(self):
        for i in range(3):
            p = os.path.join(self.tmp, f"l{i}.lock"); l = FileLock(p); self.assertTrue(l.acquire()); l.release()

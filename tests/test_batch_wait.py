import unittest
from noesis_harness.batch_wait import BatchWait

class TestBatchWait(unittest.TestCase):
    def test_wait_batch(self): m = BatchWait(); self.assertEqual(m.wait_batch({"a": 1, "b": 2}), {"a": 1, "b": 2})
    def test_existing(self): m = BatchWait(); m.set("a", 1); self.assertEqual(m.wait_batch({"a": 2}), {"a": 1})
    def test_get(self): m = BatchWait(); m.set("k", 1); self.assertEqual(m.get("k"), 1)
    def test_get_default(self): self.assertEqual(BatchWait().get("x", 5), 5)
    def test_invalidate(self): m = BatchWait(); m.set("k", 1); self.assertTrue(m.invalidate("k")); self.assertFalse(m.invalidate("k"))
    def test_clear(self): m = BatchWait(); m.set("a", 1); m.set("b", 2); self.assertEqual(m.clear(), 2); self.assertEqual(len(m), 0)
    def test_len(self): m = BatchWait(); m.set("a", 1); m.set("b", 2); self.assertEqual(len(m), 2)
    def test_deterministic(self): m = BatchWait(); m.set("a", 1); self.assertEqual(m.get("a"), m.get("a"))
    def test_many(self): m = BatchWait(); [m.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(m), 5)
    def test_no_crash(self): self.assertEqual(BatchWait().wait_batch({}), {})

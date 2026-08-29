import unittest
from noesis_harness.batch_core import BatchCore

class TestBatchCore(unittest.TestCase):
    def test_core_batch(self): m = BatchCore(); self.assertEqual(m.core_batch({"a": 1, "b": 2}), {"a": 1, "b": 2})
    def test_existing(self): m = BatchCore(); m.set("a", 1); self.assertEqual(m.core_batch({"a": 2}), {"a": 1})
    def test_get(self): m = BatchCore(); m.set("k", 1); self.assertEqual(m.get("k"), 1)
    def test_get_default(self): self.assertEqual(BatchCore().get("x", 5), 5)
    def test_invalidate(self): m = BatchCore(); m.set("k", 1); self.assertTrue(m.invalidate("k")); self.assertFalse(m.invalidate("k"))
    def test_clear(self): m = BatchCore(); m.set("a", 1); m.set("b", 2); self.assertEqual(m.clear(), 2); self.assertEqual(len(m), 0)
    def test_len(self): m = BatchCore(); m.set("a", 1); m.set("b", 2); self.assertEqual(len(m), 2)
    def test_deterministic(self): m = BatchCore(); m.set("a", 1); self.assertEqual(m.get("a"), m.get("a"))
    def test_many(self): m = BatchCore(); [m.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(m), 5)
    def test_no_crash(self): self.assertEqual(BatchCore().core_batch({}), {})

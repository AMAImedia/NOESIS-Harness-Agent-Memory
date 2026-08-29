import unittest
from noesis_harness.batch_facade import BatchFacade

class TestBatchFacade(unittest.TestCase):
    def test_cache_batch(self): m = BatchFacade(); self.assertEqual(m.cache_batch({"a": 1, "b": 2}), {"a": 1, "b": 2})
    def test_get_batch(self): m = BatchFacade(); m.set("a", 1); m.set("b", 2); self.assertEqual(m.get_batch(["a", "b"]), {"a": 1, "b": 2})
    def test_missing(self): self.assertEqual(BatchFacade().get_batch(["x"]), {})
    def test_get(self): m = BatchFacade(); m.set("k", 1); self.assertEqual(m.get("k"), 1)
    def test_get_default(self): self.assertEqual(BatchFacade().get("x", 5), 5)
    def test_invalidate(self): m = BatchFacade(); m.set("k", 1); self.assertTrue(m.invalidate("k")); self.assertFalse(m.invalidate("k"))
    def test_clear(self): m = BatchFacade(); m.set("a", 1); m.set("b", 2); self.assertEqual(m.clear(), 2); self.assertEqual(len(m), 0)
    def test_len(self): m = BatchFacade(); m.set("a", 1); m.set("b", 2); self.assertEqual(len(m), 2)
    def test_deterministic(self): m = BatchFacade(); m.set("a", 1); self.assertEqual(m.get("a"), m.get("a"))
    def test_many(self): m = BatchFacade(); [m.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(m), 5)

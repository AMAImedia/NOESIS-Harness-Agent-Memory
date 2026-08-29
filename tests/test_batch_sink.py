import unittest
from noesis_harness.batch_sink import BatchSink

class TestBatchSink(unittest.TestCase):
    def test_sink_batch(self): m = BatchSink(); self.assertEqual(m.sink_batch({"a": 1, "b": 2}), {"a": 1, "b": 2})
    def test_existing(self): m = BatchSink(); m.set("a", 1); self.assertEqual(m.sink_batch({"a": 2}), {"a": 1})
    def test_get(self): m = BatchSink(); m.set("k", 1); self.assertEqual(m.get("k"), 1)
    def test_get_default(self): self.assertEqual(BatchSink().get("x", 5), 5)
    def test_invalidate(self): m = BatchSink(); m.set("k", 1); self.assertTrue(m.invalidate("k")); self.assertFalse(m.invalidate("k"))
    def test_clear(self): m = BatchSink(); m.set("a", 1); m.set("b", 2); self.assertEqual(m.clear(), 2); self.assertEqual(len(m), 0)
    def test_len(self): m = BatchSink(); m.set("a", 1); m.set("b", 2); self.assertEqual(len(m), 2)
    def test_deterministic(self): m = BatchSink(); m.set("a", 1); self.assertEqual(m.get("a"), m.get("a"))
    def test_many(self): m = BatchSink(); [m.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(m), 5)
    def test_no_crash(self): self.assertEqual(BatchSink().sink_batch({}), {})

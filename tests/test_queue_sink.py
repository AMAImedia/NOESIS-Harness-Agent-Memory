import unittest
from noesis_harness.queue_sink import QueueSink

class TestQueueSink(unittest.TestCase):
    def test_sink(self): qs = QueueSink(5); self.assertEqual(qs.sink("a", 1), 1)
    def test_existing(self): qs = QueueSink(5); qs.sink("a", 1); self.assertEqual(qs.sink("a", 2), 2)
    def test_overflow(self): qs = QueueSink(2); qs.sink("a", 1); qs.sink("b", 2); qs.sink("c", 3); self.assertEqual(len(qs), 2); self.assertIsNotNone(qs.get("c"))
    def test_get(self): qs = QueueSink(5); qs.set("k", 1); self.assertEqual(qs.get("k"), 1)
    def test_get_default(self): self.assertEqual(QueueSink(5).get("x", 5), 5)
    def test_invalidate(self): qs = QueueSink(5); qs.set("a", 1); self.assertTrue(qs.invalidate("a")); self.assertIsNone(qs.get("a"))
    def test_clear(self): qs = QueueSink(5); qs.set("a", 1); qs.set("b", 2); self.assertEqual(qs.clear(), 2); self.assertEqual(len(qs), 0)
    def test_len(self): qs = QueueSink(5); qs.set("a", 1); qs.set("b", 2); self.assertEqual(len(qs), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): QueueSink(-1)
    def test_deterministic(self): qs = QueueSink(5); qs.set("a", 1); self.assertEqual(qs.get("a"), qs.get("a"))
    def test_many(self): qs = QueueSink(10); [qs.set(f"k{i}", i) for i in range(10)]; self.assertTrue(qs.full())

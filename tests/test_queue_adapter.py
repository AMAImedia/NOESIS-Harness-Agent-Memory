import unittest
from noesis_harness.queue_adapter import QueueAdapter

class TestQueueAdapter(unittest.TestCase):
    def test_adapt(self): qa = QueueAdapter(5); self.assertEqual(qa.adapt("a", 1), 1)
    def test_existing(self): qa = QueueAdapter(5); qa.adapt("a", 1); self.assertEqual(qa.adapt("a", 2), 2)
    def test_overflow(self): qa = QueueAdapter(2); qa.adapt("a", 1); qa.adapt("b", 2); qa.adapt("c", 3); self.assertEqual(len(qa), 2); self.assertIsNotNone(qa.get("c"))
    def test_get(self): qa = QueueAdapter(5); qa.set("k", 1); self.assertEqual(qa.get("k"), 1)
    def test_get_default(self): self.assertEqual(QueueAdapter(5).get("x", 5), 5)
    def test_invalidate(self): qa = QueueAdapter(5); qa.set("a", 1); self.assertTrue(qa.invalidate("a")); self.assertIsNone(qa.get("a"))
    def test_clear(self): qa = QueueAdapter(5); qa.set("a", 1); qa.set("b", 2); self.assertEqual(qa.clear(), 2); self.assertEqual(len(qa), 0)
    def test_len(self): qa = QueueAdapter(5); qa.set("a", 1); qa.set("b", 2); self.assertEqual(len(qa), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): QueueAdapter(-1)
    def test_deterministic(self): qa = QueueAdapter(5); qa.set("a", 1); self.assertEqual(qa.get("a"), qa.get("a"))
    def test_many(self): qa = QueueAdapter(10); [qa.set(f"k{i}", i) for i in range(10)]; self.assertTrue(qa.full())

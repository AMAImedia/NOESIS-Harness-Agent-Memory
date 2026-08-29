import unittest
from noesis_harness.queue_end import QueueEnd

class TestQueueEnd(unittest.TestCase):
    def test_end(self): qe = QueueEnd(5); self.assertEqual(qe.end("a", 1), 1)
    def test_existing(self): qe = QueueEnd(5); qe.end("a", 1); self.assertEqual(qe.end("a", 2), 2)
    def test_overflow(self): qe = QueueEnd(2); qe.end("a", 1); qe.end("b", 2); qe.end("c", 3); self.assertEqual(len(qe), 2); self.assertIsNotNone(qe.get("c"))
    def test_get(self): qe = QueueEnd(5); qe.set("k", 1); self.assertEqual(qe.get("k"), 1)
    def test_get_default(self): self.assertEqual(QueueEnd(5).get("x", 5), 5)
    def test_invalidate(self): qe = QueueEnd(5); qe.set("a", 1); self.assertTrue(qe.invalidate("a")); self.assertIsNone(qe.get("a"))
    def test_clear(self): qe = QueueEnd(5); qe.set("a", 1); qe.set("b", 2); self.assertEqual(qe.clear(), 2); self.assertEqual(len(qe), 0)
    def test_len(self): qe = QueueEnd(5); qe.set("a", 1); qe.set("b", 2); self.assertEqual(len(qe), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): QueueEnd(-1)
    def test_deterministic(self): qe = QueueEnd(5); qe.set("a", 1); self.assertEqual(qe.get("a"), qe.get("a"))
    def test_many(self): qe = QueueEnd(10); [qe.set(f"k{i}", i) for i in range(10)]; self.assertTrue(qe.full())

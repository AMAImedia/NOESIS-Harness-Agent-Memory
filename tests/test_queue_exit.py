import unittest
from noesis_harness.queue_exit import QueueExit

class TestQueueExit(unittest.TestCase):
    def test_exit(self): qe = QueueExit(5); self.assertEqual(qe.exit("a", 1), 1)
    def test_existing(self): qe = QueueExit(5); qe.exit("a", 1); self.assertEqual(qe.exit("a", 2), 2)
    def test_overflow(self): qe = QueueExit(2); qe.exit("a", 1); qe.exit("b", 2); qe.exit("c", 3); self.assertEqual(len(qe), 2); self.assertIsNotNone(qe.get("c"))
    def test_get(self): qe = QueueExit(5); qe.set("k", 1); self.assertEqual(qe.get("k"), 1)
    def test_get_default(self): self.assertEqual(QueueExit(5).get("x", 5), 5)
    def test_invalidate(self): qe = QueueExit(5); qe.set("a", 1); self.assertTrue(qe.invalidate("a")); self.assertIsNone(qe.get("a"))
    def test_clear(self): qe = QueueExit(5); qe.set("a", 1); qe.set("b", 2); self.assertEqual(qe.clear(), 2); self.assertEqual(len(qe), 0)
    def test_len(self): qe = QueueExit(5); qe.set("a", 1); qe.set("b", 2); self.assertEqual(len(qe), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): QueueExit(-1)
    def test_deterministic(self): qe = QueueExit(5); qe.set("a", 1); self.assertEqual(qe.get("a"), qe.get("a"))
    def test_many(self): qe = QueueExit(10); [qe.set(f"k{i}", i) for i in range(10)]; self.assertTrue(qe.full())

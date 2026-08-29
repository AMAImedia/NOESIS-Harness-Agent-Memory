import unittest
from noesis_harness.queue_wait import QueueWait

class TestQueueWait(unittest.TestCase):
    def test_wait(self): qw = QueueWait(5); self.assertEqual(qw.wait("a", 1), 1)
    def test_existing(self): qw = QueueWait(5); qw.wait("a", 1); self.assertEqual(qw.wait("a", 2), 2)
    def test_overflow(self): qw = QueueWait(2); qw.wait("a", 1); qw.wait("b", 2); qw.wait("c", 3); self.assertEqual(len(qw), 2); self.assertIsNotNone(qw.get("c"))
    def test_get(self): qw = QueueWait(5); qw.set("k", 1); self.assertEqual(qw.get("k"), 1)
    def test_get_default(self): self.assertEqual(QueueWait(5).get("x", 5), 5)
    def test_invalidate(self): qw = QueueWait(5); qw.set("a", 1); self.assertTrue(qw.invalidate("a")); self.assertIsNone(qw.get("a"))
    def test_clear(self): qw = QueueWait(5); qw.set("a", 1); qw.set("b", 2); self.assertEqual(qw.clear(), 2); self.assertEqual(len(qw), 0)
    def test_len(self): qw = QueueWait(5); qw.set("a", 1); qw.set("b", 2); self.assertEqual(len(qw), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): QueueWait(-1)
    def test_deterministic(self): qw = QueueWait(5); qw.set("a", 1); self.assertEqual(qw.get("a"), qw.get("a"))
    def test_many(self): qw = QueueWait(10); [qw.set(f"k{i}", i) for i in range(10)]; self.assertTrue(qw.full())

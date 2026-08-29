import unittest
from noesis_harness.queue_recv import QueueRecv

class TestQueueRecv(unittest.TestCase):
    def test_recv(self): qr = QueueRecv(5); self.assertEqual(qr.recv("a", 1), 1)
    def test_existing(self): qr = QueueRecv(5); qr.recv("a", 1); self.assertEqual(qr.recv("a", 2), 2)
    def test_overflow(self): qr = QueueRecv(2); qr.recv("a", 1); qr.recv("b", 2); qr.recv("c", 3); self.assertEqual(len(qr), 2); self.assertIsNotNone(qr.get("c"))
    def test_get(self): qr = QueueRecv(5); qr.set("k", 1); self.assertEqual(qr.get("k"), 1)
    def test_get_default(self): self.assertEqual(QueueRecv(5).get("x", 5), 5)
    def test_invalidate(self): qr = QueueRecv(5); qr.set("a", 1); self.assertTrue(qr.invalidate("a")); self.assertIsNone(qr.get("a"))
    def test_clear(self): qr = QueueRecv(5); qr.set("a", 1); qr.set("b", 2); self.assertEqual(qr.clear(), 2); self.assertEqual(len(qr), 0)
    def test_len(self): qr = QueueRecv(5); qr.set("a", 1); qr.set("b", 2); self.assertEqual(len(qr), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): QueueRecv(-1)
    def test_deterministic(self): qr = QueueRecv(5); qr.set("a", 1); self.assertEqual(qr.get("a"), qr.get("a"))
    def test_many(self): qr = QueueRecv(10); [qr.set(f"k{i}", i) for i in range(10)]; self.assertTrue(qr.full())

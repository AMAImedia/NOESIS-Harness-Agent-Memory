import unittest
from noesis_harness.ring_recv import RingRecv

class TestRingRecv(unittest.TestCase):
    def test_recv(self): rr = RingRecv(5); self.assertEqual(rr.recv("a", 1), 1)
    def test_existing(self): rr = RingRecv(5); rr.recv("a", 1); self.assertEqual(rr.recv("a", 2), 2)
    def test_overflow(self): rr = RingRecv(2); rr.recv("a", 1); rr.recv("b", 2); rr.recv("c", 3); self.assertEqual(len(rr), 2); self.assertIsNotNone(rr.get("c"))
    def test_get(self): rr = RingRecv(5); rr.set("k", 1); self.assertEqual(rr.get("k"), 1)
    def test_get_default(self): self.assertEqual(RingRecv(5).get("x", 5), 5)
    def test_invalidate(self): rr = RingRecv(5); rr.set("a", 1); self.assertTrue(rr.invalidate("a")); self.assertIsNone(rr.get("a"))
    def test_clear(self): rr = RingRecv(5); rr.set("a", 1); rr.set("b", 2); self.assertEqual(rr.clear(), 2); self.assertEqual(len(rr), 0)
    def test_len(self): rr = RingRecv(5); rr.set("a", 1); rr.set("b", 2); self.assertEqual(len(rr), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingRecv(0)
    def test_deterministic(self): rr = RingRecv(5); rr.set("a", 1); self.assertEqual(rr.get("a"), rr.get("a"))
    def test_many(self): rr = RingRecv(10); [rr.set(f"k{i}", i) for i in range(10)]; self.assertTrue(rr.full())

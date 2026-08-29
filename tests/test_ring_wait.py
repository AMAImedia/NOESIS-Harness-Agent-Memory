import unittest
from noesis_harness.ring_wait import RingWait

class TestRingWait(unittest.TestCase):
    def test_wait(self): rw = RingWait(5); self.assertEqual(rw.wait("a", 1), 1)
    def test_existing(self): rw = RingWait(5); rw.wait("a", 1); self.assertEqual(rw.wait("a", 2), 2)
    def test_overflow(self): rw = RingWait(2); rw.wait("a", 1); rw.wait("b", 2); rw.wait("c", 3); self.assertEqual(len(rw), 2); self.assertIsNotNone(rw.get("c"))
    def test_get(self): rw = RingWait(5); rw.set("k", 1); self.assertEqual(rw.get("k"), 1)
    def test_get_default(self): self.assertEqual(RingWait(5).get("x", 5), 5)
    def test_invalidate(self): rw = RingWait(5); rw.set("a", 1); self.assertTrue(rw.invalidate("a")); self.assertIsNone(rw.get("a"))
    def test_clear(self): rw = RingWait(5); rw.set("a", 1); rw.set("b", 2); self.assertEqual(rw.clear(), 2); self.assertEqual(len(rw), 0)
    def test_len(self): rw = RingWait(5); rw.set("a", 1); rw.set("b", 2); self.assertEqual(len(rw), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingWait(0)
    def test_deterministic(self): rw = RingWait(5); rw.set("a", 1); self.assertEqual(rw.get("a"), rw.get("a"))
    def test_many(self): rw = RingWait(10); [rw.set(f"k{i}", i) for i in range(10)]; self.assertTrue(rw.full())

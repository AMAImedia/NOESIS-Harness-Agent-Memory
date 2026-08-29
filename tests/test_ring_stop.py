import unittest
from noesis_harness.ring_stop import RingStop

class TestRingStop(unittest.TestCase):
    def test_stop(self): rs = RingStop(5); self.assertEqual(rs.stop("a", 1), 1)
    def test_existing(self): rs = RingStop(5); rs.stop("a", 1); self.assertEqual(rs.stop("a", 2), 2)
    def test_overflow(self): rs = RingStop(2); rs.stop("a", 1); rs.stop("b", 2); rs.stop("c", 3); self.assertEqual(len(rs), 2); self.assertIsNotNone(rs.get("c"))
    def test_get(self): rs = RingStop(5); rs.set("k", 1); self.assertEqual(rs.get("k"), 1)
    def test_get_default(self): self.assertEqual(RingStop(5).get("x", 5), 5)
    def test_invalidate(self): rs = RingStop(5); rs.set("a", 1); self.assertTrue(rs.invalidate("a")); self.assertIsNone(rs.get("a"))
    def test_clear(self): rs = RingStop(5); rs.set("a", 1); rs.set("b", 2); self.assertEqual(rs.clear(), 2); self.assertEqual(len(rs), 0)
    def test_len(self): rs = RingStop(5); rs.set("a", 1); rs.set("b", 2); self.assertEqual(len(rs), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingStop(0)
    def test_deterministic(self): rs = RingStop(5); rs.set("a", 1); self.assertEqual(rs.get("a"), rs.get("a"))
    def test_many(self): rs = RingStop(10); [rs.set(f"k{i}", i) for i in range(10)]; self.assertTrue(rs.full())

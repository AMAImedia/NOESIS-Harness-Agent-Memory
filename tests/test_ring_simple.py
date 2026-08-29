import unittest
from noesis_harness.ring_simple import RingSimple

class TestRingSimple(unittest.TestCase):
    def test_remember(self): rs = RingSimple(5); self.assertEqual(rs.remember("a", 1), 1)
    def test_existing(self): rs = RingSimple(5); rs.remember("a", 1); self.assertEqual(rs.remember("a", 2), 2)
    def test_overflow(self): rs = RingSimple(2); rs.remember("a", 1); rs.remember("b", 2); rs.remember("c", 3); self.assertEqual(len(rs), 2); self.assertIsNotNone(rs.get("c"))
    def test_get(self): rs = RingSimple(5); rs.set("k", 1); self.assertEqual(rs.get("k"), 1)
    def test_get_default(self): self.assertEqual(RingSimple(5).get("x", 5), 5)
    def test_invalidate(self): rs = RingSimple(5); rs.set("a", 1); self.assertTrue(rs.invalidate("a")); self.assertIsNone(rs.get("a"))
    def test_clear(self): rs = RingSimple(5); rs.set("a", 1); rs.set("b", 2); self.assertEqual(rs.clear(), 2); self.assertEqual(len(rs), 0)
    def test_len(self): rs = RingSimple(5); rs.set("a", 1); rs.set("b", 2); self.assertEqual(len(rs), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingSimple(0)
    def test_deterministic(self): rs = RingSimple(5); rs.set("a", 1); self.assertEqual(rs.get("a"), rs.get("a"))
    def test_many(self): rs = RingSimple(10); [rs.set(f"k{i}", i) for i in range(10)]; self.assertTrue(rs.full())

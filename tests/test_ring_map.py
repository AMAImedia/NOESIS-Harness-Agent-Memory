import unittest
from noesis_harness.ring_map import RingMap

class TestRingMap(unittest.TestCase):
    def test_mapping(self): rm = RingMap(5); self.assertEqual(rm.mapping("a", 1), 1)
    def test_existing(self): rm = RingMap(5); rm.mapping("a", 1); self.assertEqual(rm.mapping("a", 2), 2)
    def test_overflow(self): rm = RingMap(2); rm.mapping("a", 1); rm.mapping("b", 2); rm.mapping("c", 3); self.assertEqual(len(rm), 2); self.assertIsNotNone(rm.get("c"))
    def test_get(self): rm = RingMap(5); rm.set("k", 1); self.assertEqual(rm.get("k"), 1)
    def test_get_default(self): self.assertEqual(RingMap(5).get("x", 5), 5)
    def test_invalidate(self): rm = RingMap(5); rm.set("a", 1); self.assertTrue(rm.invalidate("a")); self.assertIsNone(rm.get("a"))
    def test_clear(self): rm = RingMap(5); rm.set("a", 1); rm.set("b", 2); self.assertEqual(rm.clear(), 2); self.assertEqual(len(rm), 0)
    def test_len(self): rm = RingMap(5); rm.set("a", 1); rm.set("b", 2); self.assertEqual(len(rm), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingMap(0)
    def test_deterministic(self): rm = RingMap(5); rm.set("a", 1); self.assertEqual(rm.get("a"), rm.get("a"))
    def test_many(self): rm = RingMap(10); [rm.set(f"k{i}", i) for i in range(10)]; self.assertTrue(rm.full())

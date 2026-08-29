import unittest
from noesis_harness.ring_sink import RingSink

class TestRingSink(unittest.TestCase):
    def test_sink(self): rs = RingSink(5); self.assertEqual(rs.sink("a", 1), 1)
    def test_existing(self): rs = RingSink(5); rs.sink("a", 1); self.assertEqual(rs.sink("a", 2), 2)
    def test_overflow(self): rs = RingSink(2); rs.sink("a", 1); rs.sink("b", 2); rs.sink("c", 3); self.assertEqual(len(rs), 2); self.assertIsNotNone(rs.get("c"))
    def test_get(self): rs = RingSink(5); rs.set("k", 1); self.assertEqual(rs.get("k"), 1)
    def test_get_default(self): self.assertEqual(RingSink(5).get("x", 5), 5)
    def test_invalidate(self): rs = RingSink(5); rs.set("a", 1); self.assertTrue(rs.invalidate("a")); self.assertIsNone(rs.get("a"))
    def test_clear(self): rs = RingSink(5); rs.set("a", 1); rs.set("b", 2); self.assertEqual(rs.clear(), 2); self.assertEqual(len(rs), 0)
    def test_len(self): rs = RingSink(5); rs.set("a", 1); rs.set("b", 2); self.assertEqual(len(rs), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingSink(0)
    def test_deterministic(self): rs = RingSink(5); rs.set("a", 1); self.assertEqual(rs.get("a"), rs.get("a"))
    def test_many(self): rs = RingSink(10); [rs.set(f"k{i}", i) for i in range(10)]; self.assertTrue(rs.full())

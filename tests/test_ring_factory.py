import unittest
from noesis_harness.ring_factory import RingFactory

class TestRingFactory(unittest.TestCase):
    def test_get(self): rf = RingFactory(5, lambda k: k * 2); self.assertEqual(rf.get("a"), "aa")
    def test_missing(self): self.assertIsNone(RingFactory(5).get("x"))
    def test_overflow(self): rf = RingFactory(2, lambda k: k); rf.get("a"); rf.get("b"); rf.get("c"); self.assertEqual(len(rf), 2); self.assertIsNotNone(rf.get("c"))
    def test_invalidate(self): rf = RingFactory(5, lambda k: k); rf.get("a"); self.assertTrue(rf.invalidate("a")); self.assertIsNone(rf.get("a"))
    def test_clear(self): rf = RingFactory(5, lambda k: k); rf.get("a"); rf.get("b"); self.assertEqual(rf.clear(), 2); self.assertEqual(len(rf), 0)
    def test_len(self): rf = RingFactory(5, lambda k: k); rf.get("a"); rf.get("b"); self.assertEqual(len(rf), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingFactory(0)
    def test_deterministic(self): rf = RingFactory(5, lambda k: 5); self.assertEqual(rf.get("a"), rf.get("a"))
    def test_many(self): rf = RingFactory(10, lambda k: k); [rf.get(f"k{i}") for i in range(10)]; self.assertTrue(rf.full())
    def test_no_factory(self): self.assertIsNone(RingFactory(5).get("x"))

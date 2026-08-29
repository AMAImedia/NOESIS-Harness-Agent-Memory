import unittest
from noesis_harness.ring_halt_done import RingHaltDone

class TestRingHaltDone(unittest.TestCase):
    def test_halt_done(self): rh = RingHaltDone(5); self.assertEqual(rh.halt_done("a", 1), 1)
    def test_existing(self): rh = RingHaltDone(5); rh.halt_done("a", 1); self.assertEqual(rh.halt_done("a", 2), 2)
    def test_overflow(self): rh = RingHaltDone(2); rh.halt_done("a", 1); rh.halt_done("b", 2); rh.halt_done("c", 3); self.assertEqual(len(rh), 2); self.assertIsNotNone(rh.get("c"))
    def test_get(self): rh = RingHaltDone(5); rh.set("k", 1); self.assertEqual(rh.get("k"), 1)
    def test_get_default(self): self.assertEqual(RingHaltDone(5).get("x", 5), 5)
    def test_invalidate(self): rh = RingHaltDone(5); rh.set("a", 1); self.assertTrue(rh.invalidate("a")); self.assertIsNone(rh.get("a"))
    def test_clear(self): rh = RingHaltDone(5); rh.set("a", 1); rh.set("b", 2); self.assertEqual(rh.clear(), 2); self.assertEqual(len(rh), 0)
    def test_len(self): rh = RingHaltDone(5); rh.set("a", 1); rh.set("b", 2); self.assertEqual(len(rh), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingHaltDone(0)
    def test_deterministic(self): rh = RingHaltDone(5); rh.set("a", 1); self.assertEqual(rh.get("a"), rh.get("a"))
    def test_many(self): rh = RingHaltDone(10); [rh.set(f"k{i}", i) for i in range(10)]; self.assertTrue(rh.full())

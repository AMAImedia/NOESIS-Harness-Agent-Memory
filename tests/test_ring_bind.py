import unittest
from noesis_harness.ring_bind import RingBind

class TestRingBind(unittest.TestCase):
    def test_binding(self): rb = RingBind(5); self.assertEqual(rb.binding("a", 1), 1)
    def test_existing(self): rb = RingBind(5); rb.binding("a", 1); self.assertEqual(rb.binding("a", 2), 2)
    def test_overflow(self): rb = RingBind(2); rb.binding("a", 1); rb.binding("b", 2); rb.binding("c", 3); self.assertEqual(len(rb), 2); self.assertIsNotNone(rb.get("c"))
    def test_get(self): rb = RingBind(5); rb.set("k", 1); self.assertEqual(rb.get("k"), 1)
    def test_get_default(self): self.assertEqual(RingBind(5).get("x", 5), 5)
    def test_invalidate(self): rb = RingBind(5); rb.set("a", 1); self.assertTrue(rb.invalidate("a")); self.assertIsNone(rb.get("a"))
    def test_clear(self): rb = RingBind(5); rb.set("a", 1); rb.set("b", 2); self.assertEqual(rb.clear(), 2); self.assertEqual(len(rb), 0)
    def test_len(self): rb = RingBind(5); rb.set("a", 1); rb.set("b", 2); self.assertEqual(len(rb), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingBind(0)
    def test_deterministic(self): rb = RingBind(5); rb.set("a", 1); self.assertEqual(rb.get("a"), rb.get("a"))
    def test_many(self): rb = RingBind(10); [rb.set(f"k{i}", i) for i in range(10)]; self.assertTrue(rb.full())

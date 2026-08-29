import unittest
from noesis_harness.ring_node import RingNode

class TestRingNode(unittest.TestCase):
    def test_node(self): rn = RingNode(5); self.assertEqual(rn.node("a", 1), 1)
    def test_existing(self): rn = RingNode(5); rn.node("a", 1); self.assertEqual(rn.node("a", 2), 2)
    def test_overflow(self): rn = RingNode(2); rn.node("a", 1); rn.node("b", 2); rn.node("c", 3); self.assertEqual(len(rn), 2); self.assertIsNotNone(rn.get("c"))
    def test_get(self): rn = RingNode(5); rn.set("k", 1); self.assertEqual(rn.get("k"), 1)
    def test_get_default(self): self.assertEqual(RingNode(5).get("x", 5), 5)
    def test_invalidate(self): rn = RingNode(5); rn.set("a", 1); self.assertTrue(rn.invalidate("a")); self.assertIsNone(rn.get("a"))
    def test_clear(self): rn = RingNode(5); rn.set("a", 1); rn.set("b", 2); self.assertEqual(rn.clear(), 2); self.assertEqual(len(rn), 0)
    def test_len(self): rn = RingNode(5); rn.set("a", 1); rn.set("b", 2); self.assertEqual(len(rn), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingNode(0)
    def test_deterministic(self): rn = RingNode(5); rn.set("a", 1); self.assertEqual(rn.get("a"), rn.get("a"))
    def test_many(self): rn = RingNode(10); [rn.set(f"k{i}", i) for i in range(10)]; self.assertTrue(rn.full())

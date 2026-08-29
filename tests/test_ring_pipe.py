import unittest
from noesis_harness.ring_pipe import RingPipe

class TestRingPipe(unittest.TestCase):
    def test_pipe(self): rp = RingPipe(5); self.assertEqual(rp.pipe("a", 1), 1)
    def test_existing(self): rp = RingPipe(5); rp.pipe("a", 1); self.assertEqual(rp.pipe("a", 2), 2)
    def test_overflow(self): rp = RingPipe(2); rp.pipe("a", 1); rp.pipe("b", 2); rp.pipe("c", 3); self.assertEqual(len(rp), 2); self.assertIsNotNone(rp.get("c"))
    def test_get(self): rp = RingPipe(5); rp.set("k", 1); self.assertEqual(rp.get("k"), 1)
    def test_get_default(self): self.assertEqual(RingPipe(5).get("x", 5), 5)
    def test_invalidate(self): rp = RingPipe(5); rp.set("a", 1); self.assertTrue(rp.invalidate("a")); self.assertIsNone(rp.get("a"))
    def test_clear(self): rp = RingPipe(5); rp.set("a", 1); rp.set("b", 2); self.assertEqual(rp.clear(), 2); self.assertEqual(len(rp), 0)
    def test_len(self): rp = RingPipe(5); rp.set("a", 1); rp.set("b", 2); self.assertEqual(len(rp), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingPipe(0)
    def test_deterministic(self): rp = RingPipe(5); rp.set("a", 1); self.assertEqual(rp.get("a"), rp.get("a"))
    def test_many(self): rp = RingPipe(10); [rp.set(f"k{i}", i) for i in range(10)]; self.assertTrue(rp.full())

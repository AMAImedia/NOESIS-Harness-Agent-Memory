import unittest
from noesis_harness.ring_end import RingEnd

class TestRingEnd(unittest.TestCase):
    def test_end(self): re = RingEnd(5); self.assertEqual(re.end("a", 1), 1)
    def test_existing(self): re = RingEnd(5); re.end("a", 1); self.assertEqual(re.end("a", 2), 2)
    def test_overflow(self): re = RingEnd(2); re.end("a", 1); re.end("b", 2); re.end("c", 3); self.assertEqual(len(re), 2); self.assertIsNotNone(re.get("c"))
    def test_get(self): re = RingEnd(5); re.set("k", 1); self.assertEqual(re.get("k"), 1)
    def test_get_default(self): self.assertEqual(RingEnd(5).get("x", 5), 5)
    def test_invalidate(self): re = RingEnd(5); re.set("a", 1); self.assertTrue(re.invalidate("a")); self.assertIsNone(re.get("a"))
    def test_clear(self): re = RingEnd(5); re.set("a", 1); re.set("b", 2); self.assertEqual(re.clear(), 2); self.assertEqual(len(re), 0)
    def test_len(self): re = RingEnd(5); re.set("a", 1); re.set("b", 2); self.assertEqual(len(re), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingEnd(0)
    def test_deterministic(self): re = RingEnd(5); re.set("a", 1); self.assertEqual(re.get("a"), re.get("a"))
    def test_many(self): re = RingEnd(10); [re.set(f"k{i}", i) for i in range(10)]; self.assertTrue(re.full())

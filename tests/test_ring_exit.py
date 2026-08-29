import unittest
from noesis_harness.ring_exit import RingExit

class TestRingExit(unittest.TestCase):
    def test_exit(self): re = RingExit(5); self.assertEqual(re.exit("a", 1), 1)
    def test_existing(self): re = RingExit(5); re.exit("a", 1); self.assertEqual(re.exit("a", 2), 2)
    def test_overflow(self): re = RingExit(2); re.exit("a", 1); re.exit("b", 2); re.exit("c", 3); self.assertEqual(len(re), 2); self.assertIsNotNone(re.get("c"))
    def test_get(self): re = RingExit(5); re.set("k", 1); self.assertEqual(re.get("k"), 1)
    def test_get_default(self): self.assertEqual(RingExit(5).get("x", 5), 5)
    def test_invalidate(self): re = RingExit(5); re.set("a", 1); self.assertTrue(re.invalidate("a")); self.assertIsNone(re.get("a"))
    def test_clear(self): re = RingExit(5); re.set("a", 1); re.set("b", 2); self.assertEqual(re.clear(), 2); self.assertEqual(len(re), 0)
    def test_len(self): re = RingExit(5); re.set("a", 1); re.set("b", 2); self.assertEqual(len(re), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingExit(0)
    def test_deterministic(self): re = RingExit(5); re.set("a", 1); self.assertEqual(re.get("a"), re.get("a"))
    def test_many(self): re = RingExit(10); [re.set(f"k{i}", i) for i in range(10)]; self.assertTrue(re.full())

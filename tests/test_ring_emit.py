import unittest
from noesis_harness.ring_emit import RingEmit

class TestRingEmit(unittest.TestCase):
    def test_emit(self): re = RingEmit(5); self.assertEqual(re.emit("a", 1), 1)
    def test_existing(self): re = RingEmit(5); re.emit("a", 1); self.assertEqual(re.emit("a", 2), 2)
    def test_overflow(self): re = RingEmit(2); re.emit("a", 1); re.emit("b", 2); re.emit("c", 3); self.assertEqual(len(re), 2); self.assertIsNotNone(re.get("c"))
    def test_get(self): re = RingEmit(5); re.set("k", 1); self.assertEqual(re.get("k"), 1)
    def test_get_default(self): self.assertEqual(RingEmit(5).get("x", 5), 5)
    def test_invalidate(self): re = RingEmit(5); re.set("a", 1); self.assertTrue(re.invalidate("a")); self.assertIsNone(re.get("a"))
    def test_clear(self): re = RingEmit(5); re.set("a", 1); re.set("b", 2); self.assertEqual(re.clear(), 2); self.assertEqual(len(re), 0)
    def test_len(self): re = RingEmit(5); re.set("a", 1); re.set("b", 2); self.assertEqual(len(re), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingEmit(0)
    def test_deterministic(self): re = RingEmit(5); re.set("a", 1); self.assertEqual(re.get("a"), re.get("a"))
    def test_many(self): re = RingEmit(10); [re.set(f"k{i}", i) for i in range(10)]; self.assertTrue(re.full())

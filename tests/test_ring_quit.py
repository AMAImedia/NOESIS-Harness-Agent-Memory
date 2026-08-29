import unittest
from noesis_harness.ring_quit import RingQuit

class TestRingQuit(unittest.TestCase):
    def test_quit(self): rq = RingQuit(5); self.assertEqual(rq.quit("a", 1), 1)
    def test_existing(self): rq = RingQuit(5); rq.quit("a", 1); self.assertEqual(rq.quit("a", 2), 2)
    def test_overflow(self): rq = RingQuit(2); rq.quit("a", 1); rq.quit("b", 2); rq.quit("c", 3); self.assertEqual(len(rq), 2); self.assertIsNotNone(rq.get("c"))
    def test_get(self): rq = RingQuit(5); rq.set("k", 1); self.assertEqual(rq.get("k"), 1)
    def test_get_default(self): self.assertEqual(RingQuit(5).get("x", 5), 5)
    def test_invalidate(self): rq = RingQuit(5); rq.set("a", 1); self.assertTrue(rq.invalidate("a")); self.assertIsNone(rq.get("a"))
    def test_clear(self): rq = RingQuit(5); rq.set("a", 1); rq.set("b", 2); self.assertEqual(rq.clear(), 2); self.assertEqual(len(rq), 0)
    def test_len(self): rq = RingQuit(5); rq.set("a", 1); rq.set("b", 2); self.assertEqual(len(rq), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingQuit(0)
    def test_deterministic(self): rq = RingQuit(5); rq.set("a", 1); self.assertEqual(rq.get("a"), rq.get("a"))
    def test_many(self): rq = RingQuit(10); [rq.set(f"k{i}", i) for i in range(10)]; self.assertTrue(rq.full())

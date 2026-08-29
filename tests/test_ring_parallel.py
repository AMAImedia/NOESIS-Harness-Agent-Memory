import threading, unittest
from noesis_harness.ring_parallel import RingParallel

class TestRingParallel(unittest.TestCase):
    def test_push_pop(self): r = RingParallel(3); r.push(1); r.push(2); self.assertEqual(r.pop(), 1)
    def test_empty(self): r = RingParallel(3); self.assertIsNone(r.pop()); self.assertTrue(r.empty())
    def test_full(self): r = RingParallel(2); r.push(1); r.push(2); self.assertTrue(r.full()); self.assertFalse(r.push(3))
    def test_len(self): r = RingParallel(3); r.push(1); r.push(2); self.assertEqual(len(r), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingParallel(0)
    def test_thread_safe(self):
        r = RingParallel(100); pushed = [0]
        def worker():
            for _ in range(50):
                if r.push(1): pushed[0] += 1
        threads = [threading.Thread(target=worker) for _ in range(3)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(pushed[0], 100)
    def test_deterministic(self): r = RingParallel(3); r.push(1); self.assertEqual(r.pop(), 1)
    def test_many(self): r = RingParallel(5); [r.push(i) for i in range(5)]; self.assertTrue(r.full())
    def test_no_crash(self): r = RingParallel(1); r.push(1); r.pop(); r.push(2)
    def test_cycle(self): r = RingParallel(2); r.push(1); r.push(2); r.pop(); r.push(3); self.assertEqual(r.pop(), 2)

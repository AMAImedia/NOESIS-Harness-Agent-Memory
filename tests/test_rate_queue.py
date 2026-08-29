import time, unittest
from noesis_harness.rate_queue import RateQueue

class TestRateQueue(unittest.TestCase):
    def test_push_pop(self): rq = RateQueue(3); rq.push(1); rq.push(2); self.assertEqual(rq.pop(), 1)
    def test_empty(self): rq = RateQueue(3); self.assertIsNone(rq.pop()); self.assertTrue(rq.empty())
    def test_full(self): rq = RateQueue(2, 0.01); rq.push(1); rq.push(2); self.assertTrue(rq.full()); self.assertFalse(rq.push(3))
    def test_refill(self): rq = RateQueue(2, 0.01); rq.push(1); rq.push(2); time.sleep(0.02); self.assertTrue(rq.push(3))
    def test_peek(self): rq = RateQueue(3); rq.push(1); self.assertEqual(rq.peek(), 1); self.assertEqual(len(rq), 1)
    def test_invalid(self):
        with self.assertRaises(ValueError): RateQueue(0)
    def test_len(self): rq = RateQueue(3); rq.push(1); rq.push(2); self.assertEqual(len(rq), 2)
    def test_deterministic(self): rq = RateQueue(3); rq.push(1); self.assertEqual(rq.peek(), 1)
    def test_many(self): rq = RateQueue(5); [rq.push(i) for i in range(5)]; self.assertTrue(rq.full())
    def test_no_crash(self): rq = RateQueue(1); rq.push(1); rq.pop(); rq.push(2)

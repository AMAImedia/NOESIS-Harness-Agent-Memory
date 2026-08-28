import threading, unittest
from noesis_harness.counter import Counter

class TestCounter(unittest.TestCase):
    def test_inc(self): c = Counter(); self.assertEqual(c.inc(), 1); self.assertEqual(c.inc(2), 3)
    def test_dec(self): c = Counter(5); self.assertEqual(c.dec(), 4)
    def test_get(self): c = Counter(2); self.assertEqual(c.get(), 2)
    def test_reset(self): c = Counter(5); c.reset(); self.assertEqual(c.get(), 0)
    def test_initial(self): self.assertEqual(Counter(10).get(), 10)
    def test_negative(self): c = Counter(); c.dec(5); self.assertEqual(c.get(), -5)
    def test_thread(self):
        c = Counter()
        def inc_many(): [c.inc() for _ in range(100)]
        ts = [threading.Thread(target=inc_many) for _ in range(5)]
        [t.start() for t in ts]; [t.join() for t in ts]; self.assertEqual(c.get(), 500)
    def test_determinism(self): a = Counter(); b = Counter(); a.inc(2); b.inc(2); self.assertEqual(a.get(), b.get())
    def test_inc_return(self): c = Counter(); self.assertEqual(c.inc(), c.get())
    def test_zero(self): c = Counter(); self.assertEqual(c.inc(0), 0)

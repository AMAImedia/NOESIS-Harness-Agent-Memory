import unittest
from noesis_harness.timer_wheel import TimerWheel

class TestTimerWheel(unittest.TestCase):
    def test_fire(self):
        fired = []
        w = TimerWheel(60); w.add(2, lambda: fired.append(1))
        self.assertEqual(w.tick(0), 0); self.assertEqual(w.tick(1), 0); self.assertEqual(w.tick(2), 1)
        self.assertEqual(fired, [1])
    def test_no_fire_before(self): fired = []; w = TimerWheel(60); w.add(5, lambda: fired.append(1)); self.assertEqual(w.tick(4), 0); self.assertEqual(fired, [])
    def test_many(self):
        fired = []
        w = TimerWheel(10)
        for i in range(5): w.add(i, lambda i=i: fired.append(i))
        total = 0
        for now in range(5): total += w.tick(now)
        self.assertEqual(total, 5); self.assertEqual(sorted(fired), [0, 1, 2, 3, 4])
    def test_invalid_slots(self):
        with self.assertRaises(ValueError): TimerWheel(0)
    def test_invalid_delay(self):
        with self.assertRaises(ValueError): TimerWheel(60).add(-1, lambda: None)
    def test_repeat_slot(self): fired = []; w = TimerWheel(4); w.add(2, lambda: fired.append(1)); w.add(6, lambda: fired.append(2)); self.assertEqual(w.tick(2), 1); self.assertEqual(w.tick(6), 1); self.assertEqual(fired, [1, 2])
    def test_determinism(self):
        a = TimerWheel(8); b = TimerWheel(8); a.add(3, lambda: None); b.add(3, lambda: None); self.assertEqual(a.tick(3), b.tick(3))
    def test_empty(self): self.assertEqual(TimerWheel(5).tick(0), 0)
    def test_zero_delay(self): fired = []; w = TimerWheel(5); w.add(0, lambda: fired.append(1)); self.assertEqual(w.tick(0), 1)
    def test_wrap(self): fired = []; w = TimerWheel(3); w.add(3, lambda: fired.append(1)); self.assertEqual(w.tick(3), 1)

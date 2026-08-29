import time, unittest
from noesis_harness.rate_bind import RateBind

class TestRateBind(unittest.TestCase):
    def test_binding(self): rb = RateBind(10); self.assertEqual(rb.binding("a", 1), 1)
    def test_cached(self): rb = RateBind(10); rb.binding("a", 1); self.assertEqual(rb.binding("a", 2), 1)
    def test_get(self): rb = RateBind(10); rb.set("a", 1); self.assertEqual(rb.get("a"), 1)
    def test_get_default(self): self.assertEqual(RateBind(10).get("x", 5), 5)
    def test_ttl(self): rb = RateBind(0.01); rb.set("a", 1); time.sleep(0.02); self.assertIsNone(rb.get("a"))
    def test_invalidate(self): rb = RateBind(10); rb.set("a", 1); self.assertTrue(rb.invalidate("a")); self.assertFalse(rb.invalidate("a"))
    def test_clear(self): rb = RateBind(10); rb.set("a", 1); rb.set("b", 2); self.assertEqual(rb.clear(), 2); self.assertEqual(len(rb), 0)
    def test_len(self): rb = RateBind(10); rb.set("a", 1); rb.set("b", 2); self.assertEqual(len(rb), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RateBind(0)
    def test_deterministic(self): rb = RateBind(10); rb.set("a", 1); self.assertEqual(rb.get("a"), rb.get("a"))
    def test_many(self): rb = RateBind(10); [rb.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(rb), 5)

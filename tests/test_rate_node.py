import time, unittest
from noesis_harness.rate_node import RateNode

class TestRateNode(unittest.TestCase):
    def test_node(self): rn = RateNode(10); self.assertEqual(rn.node("a", 1), 1)
    def test_cached(self): rn = RateNode(10); rn.node("a", 1); self.assertEqual(rn.node("a", 2), 1)
    def test_get(self): rn = RateNode(10); rn.set("a", 1); self.assertEqual(rn.get("a"), 1)
    def test_get_default(self): self.assertEqual(RateNode(10).get("x", 5), 5)
    def test_ttl(self): rn = RateNode(0.01); rn.set("a", 1); time.sleep(0.02); self.assertIsNone(rn.get("a"))
    def test_invalidate(self): rn = RateNode(10); rn.set("a", 1); self.assertTrue(rn.invalidate("a")); self.assertFalse(rn.invalidate("a"))
    def test_clear(self): rn = RateNode(10); rn.set("a", 1); rn.set("b", 2); self.assertEqual(rn.clear(), 2); self.assertEqual(len(rn), 0)
    def test_len(self): rn = RateNode(10); rn.set("a", 1); rn.set("b", 2); self.assertEqual(len(rn), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RateNode(0)
    def test_deterministic(self): rn = RateNode(10); rn.set("a", 1); self.assertEqual(rn.get("a"), rn.get("a"))
    def test_many(self): rn = RateNode(10); [rn.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(rn), 5)

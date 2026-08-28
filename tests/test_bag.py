import unittest
from noesis_harness.bag import Bag

class TestBag(unittest.TestCase):
    def test_add(self): b = Bag(); b.add("a"); self.assertEqual(b.count("a"), 1)
    def test_multi(self): b = Bag(); b.add("a", 3); self.assertEqual(b.count("a"), 3)
    def test_remove(self): b = Bag(); b.add("a", 3); b.remove("a", 1); self.assertEqual(b.count("a"), 2)
    def test_remove_zero(self): b = Bag(); b.add("a", 2); b.remove("a", 2); self.assertEqual(b.count("a"), 0); self.assertEqual(b.distinct(), 0)
    def test_missing(self): self.assertEqual(Bag().count("x"), 0)
    def test_distinct(self): b = Bag(); b.add("a"); b.add("b", 2); self.assertEqual(b.distinct(), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): Bag().add("a", -1)
    def test_determinism(self): a = Bag(); b = Bag(); a.add("x", 2); b.add("x", 2); self.assertEqual(a.count("x"), b.count("x"))
    def test_items(self): b = Bag(); b.add("a"); b.add("b"); self.assertEqual(set(b.items()), {("a", 1), ("b", 1)})
    def test_many(self):
        b = Bag()
        for i in range(5): b.add(f"k{i}")
        self.assertEqual(b.distinct(), 5)

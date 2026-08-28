import unittest
from noesis_harness.bitset import BitSet

class TestBitSet(unittest.TestCase):
    def test_set_test(self): b = BitSet(8); b.set(0); self.assertTrue(b.test(0)); self.assertFalse(b.test(1))
    def test_clear(self): b = BitSet(8); b.set(3); b.clear(3); self.assertFalse(b.test(3))
    def test_count(self): b = BitSet(8); b.set(0); b.set(3); self.assertEqual(b.count(), 2)
    def test_invalid_size(self):
        with self.assertRaises(ValueError): BitSet(-1)
    def test_out_of_range(self):
        b = BitSet(4); b.set(0); b.clear(0)
        with self.assertRaises(IndexError): b.set(4)
    def test_empty_count(self): self.assertEqual(BitSet(0).count(), 0)
    def test_across_words(self): b = BitSet(100); b.set(0); b.set(64); self.assertEqual(b.count(), 2); self.assertTrue(b.test(64))
    def test_determinism(self): a = BitSet(10); b = BitSet(10); a.set(5); b.set(5); self.assertEqual(a.test(5), b.test(5))
    def test_many(self):
        b = BitSet(64)
        for i in range(64): b.set(i)
        self.assertEqual(b.count(), 64)
    def test_size_attr(self): self.assertEqual(BitSet(16).size, 16)

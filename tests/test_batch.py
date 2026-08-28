import unittest
from noesis_harness.batch import chunk

class TestChunk(unittest.TestCase):
    def test_chunk(self): self.assertEqual(chunk([1, 2, 3, 4], 2), [[1, 2], [3, 4]])
    def test_remainder(self): self.assertEqual(chunk([1, 2, 3], 2), [[1, 2], [3]])
    def test_empty(self): self.assertEqual(chunk([], 2), [])
    def test_size_one(self): self.assertEqual(chunk([1, 2], 1), [[1], [2]])
    def test_larger_than_list(self): self.assertEqual(chunk([1, 2], 10), [[1, 2]])
    def test_invalid(self):
        with self.assertRaises(ValueError): chunk([1], 0)
    def test_determinism(self): self.assertEqual(chunk([1, 2, 3], 2), chunk([1, 2, 3], 2))
    def test_no_mutation(self): a = [1, 2, 3]; chunk(a, 2); self.assertEqual(a, [1, 2, 3])
    def test_exact(self): self.assertEqual(chunk([1, 2, 3, 4], 4), [[1, 2, 3, 4]])
    def test_strings(self): self.assertEqual(chunk(["a", "b", "c"], 2), [["a", "b"], ["c"]])

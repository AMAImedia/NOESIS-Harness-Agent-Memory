import unittest
from noesis_harness.paginator import page, total_pages

class TestPaginator(unittest.TestCase):
    def test_page(self): self.assertEqual(page(list(range(10)), 3, 0), [0, 1, 2])
    def test_page2(self): self.assertEqual(page(list(range(10)), 3, 1), [3, 4, 5])
    def test_last(self): self.assertEqual(page(list(range(10)), 3, 3), [9])
    def test_total(self): self.assertEqual(total_pages(list(range(10)), 3), 4)
    def test_invalid_size(self):
        with self.assertRaises(ValueError): page([1], 0, 0)
    def test_invalid_num(self):
        with self.assertRaises(ValueError): page([1], 3, -1)
    def test_empty(self): self.assertEqual(page([], 3, 0), [])
    def test_out_of_range(self): self.assertEqual(page(list(range(5)), 3, 10), [])
    def test_determinism(self): self.assertEqual(page(list(range(10)), 3, 1), page(list(range(10)), 3, 1))
    def test_exact(self): self.assertEqual(page(list(range(6)), 3, 1), [3, 4, 5])

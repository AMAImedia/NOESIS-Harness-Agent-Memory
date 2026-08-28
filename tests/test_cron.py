import unittest
from noesis_harness.cron import matches

class TestCron(unittest.TestCase):
    def test_star(self): self.assertTrue(matches("* * * * *", 0, 0, 1, 1, 0))
    def test_minute(self): self.assertTrue(matches("5 * * * *", 5, 0, 1, 1, 0)); self.assertFalse(matches("5 * * * *", 6, 0, 1, 1, 0))
    def test_step(self): self.assertTrue(matches("*/15 * * * *", 0, 0, 1, 1, 0)); self.assertTrue(matches("*/15 * * * *", 30, 0, 1, 1, 0)); self.assertFalse(matches("*/15 * * * *", 7, 0, 1, 1, 0))
    def test_exact(self): self.assertTrue(matches("0 0 1 1 0", 0, 0, 1, 1, 0))
    def test_list(self): self.assertTrue(matches("1,2 * * * *", 2, 0, 1, 1, 0)); self.assertFalse(matches("1,2 * * * *", 3, 0, 1, 1, 0))
    def test_invalid(self):
        with self.assertRaises(ValueError): matches("*", 0, 0, 1, 1, 0)
    def test_dow(self): self.assertTrue(matches("* * * * 1", 0, 0, 1, 1, 1)); self.assertFalse(matches("* * * * 1", 0, 0, 1, 1, 2))
    def test_month(self): self.assertTrue(matches("* * * 6 *", 0, 0, 1, 6, 0)); self.assertFalse(matches("* * * 6 *", 0, 0, 1, 7, 0))
    def test_combo(self): self.assertTrue(matches("0 12 * * 1", 0, 12, 5, 3, 1)); self.assertFalse(matches("0 12 * * 1", 0, 13, 5, 3, 1))
    def test_hour(self): self.assertTrue(matches("* 8 * * *", 0, 8, 1, 1, 0)); self.assertFalse(matches("* 8 * * *", 0, 9, 1, 1, 0))

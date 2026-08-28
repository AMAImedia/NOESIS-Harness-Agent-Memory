import unittest
from noesis_harness.table import format_table

class TestTable(unittest.TestCase):
    def test_basic(self):
        t = format_table(["a", "b"], [["1", "2"]])
        self.assertIn("a", t); self.assertIn("b", t); self.assertIn("1", t)
    def test_width(self): t = format_table(["name"], [["x"]]); self.assertIn("name", t)
    def test_empty(self): t = format_table(["a"], []); self.assertIn("a", t); self.assertIn("+", t)
    def test_separator(self): t = format_table(["a", "b"], [["1", "2"]]); self.assertIn("+", t)
    def test_alignment(self): t = format_table(["a"], [["hi"]]); self.assertIn("hi", t)
    def test_determinism(self): self.assertEqual(format_table(["a"], [["1"]]), format_table(["a"], [["1"]]))
    def test_multiple_rows(self):
        t = format_table(["a", "b"], [["1", "2"], ["3", "4"]])
        self.assertIn("3", t); self.assertIn("4", t)
    def test_pipes(self): t = format_table(["a"], [["1"]]); self.assertTrue(t.startswith("|"))
    def test_wide(self): t = format_table(["x"], [["hello"]]); self.assertIn("hello", t)
    def test_no_crash(self): format_table(["a", "b", "c"], [["1", "2", "3"], ["4", "5", "6"]])

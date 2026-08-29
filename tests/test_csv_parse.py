import unittest
from noesis_harness.csv_parse import parse, unparse

class TestCsv(unittest.TestCase):
    def test_parse(self): self.assertEqual(parse("a,b\n1,2\n"), [["a","b"],["1","2"]])
    def test_unparse(self): self.assertEqual(unparse([["a","b"]]), "a,b\n")
    def test_roundtrip(self): rows=[["a","b, c"],["1","2"]]; self.assertEqual(parse(unparse(rows)), rows)
    def test_empty(self): self.assertEqual(parse(""), [])
    def test_quoted(self): self.assertEqual(parse('"a, b",c\n'), [["a, b","c"]])
    def test_single(self): self.assertEqual(parse("x\n"), [["x"]])
    def test_unicode(self): self.assertEqual(parse("привет,мир\n")[0], ["привет","мир"])
    def test_determinism(self): self.assertEqual(parse("a,b\n"), parse("a,b\n"))
    def test_many(self): self.assertEqual(len(parse("a,b\n"*5)),5)
    def test_newline(self): self.assertEqual(unparse([["a"]]).strip(), "a")

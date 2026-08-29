import unittest
from noesis_harness.ini_parse import parse, get

class TestIni(unittest.TestCase):
    def test_parse(self): self.assertEqual(parse("[s]\na=1\n"), {"s":{"a":"1"}})
    def test_get(self): self.assertEqual(get(parse("[s]\na=1\n"),"s","a"),"1")
    def test_default(self): self.assertEqual(get({},"x","y","d"),"d")
    def test_two_sections(self): self.assertEqual(set(parse("[a]\nx=1\n[b]\ny=2\n").keys()),{"a","b"})
    def test_empty(self): self.assertEqual(parse(""),{})
    def test_missing_section(self): self.assertIsNone(get(parse("[a]\nx=1\n"),"b","x"))
    def test_unicode(self): self.assertEqual(parse("[s]\nk=привет\n")["s"]["k"],"привет")
    def test_determinism(self): self.assertEqual(parse("[a]\nx=1\n"),parse("[a]\nx=1\n"))
    def test_comment(self): self.assertEqual(parse("[s]\n; c\na=1\n")["s"]["a"],"1")
    def test_many(self): self.assertEqual(len(parse("[a]\n"+"".join(f"k{i}={i}\n" for i in range(5)) )["a"]),5)

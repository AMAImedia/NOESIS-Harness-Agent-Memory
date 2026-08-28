import unittest
from noesis_harness.slugify import slugify

class TestSlugify(unittest.TestCase):
    def test_basic(self): self.assertEqual(slugify("Hello World"), "hello-world")
    def test_spaces(self): self.assertEqual(slugify("a  b   c"), "a-b-c")
    def test_symbols(self): self.assertEqual(slugify("Hello, World!"), "hello-world")
    def test_unicode(self): self.assertEqual(slugify("Café Münchën"), "cafe-munchen")
    def test_max_len(self): self.assertEqual(len(slugify("a b c d e f g", 5)), 5)
    def test_empty(self): self.assertEqual(slugify(""), "")
    def test_dashes(self): self.assertEqual(slugify("---"), "")
    def test_numbers(self): self.assertEqual(slugify("Item 42"), "item-42")
    def test_determinism(self): self.assertEqual(slugify("Foo Bar"), slugify("Foo Bar"))
    def test_trim(self): self.assertEqual(slugify("  Spaced  "), "spaced")

import unittest
from noesis_harness.tokenize import tokens, tokens_lower, count_words

class TestTokenize(unittest.TestCase):
    def test_basic(self): self.assertEqual(tokens("Hello world"), ["Hello", "world"])
    def test_lower(self): self.assertEqual(tokens_lower("Hello World"), ["hello", "world"])
    def test_count(self): self.assertEqual(count_words("one two three"), 3)
    def test_symbols(self): self.assertEqual(tokens("a,b.c!"), ["a", "b", "c"])
    def test_empty(self): self.assertEqual(tokens(""), [])
    def test_numbers(self): self.assertEqual(tokens("item 42 x9"), ["item", "42", "x9"])
    def test_mixed(self): self.assertEqual(tokens("Foo-bar baz"), ["Foo", "bar", "baz"])
    def test_determinism(self): self.assertEqual(tokens("a b c"), tokens("a b c"))
    def test_underscore(self): self.assertEqual(tokens("a_b c"), ["a", "b", "c"])
    def test_apostrophe(self): self.assertEqual(tokens("don't"), ["don", "t"])

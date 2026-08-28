import unittest
from noesis_harness.ngram import char_ngrams

class TestNGram(unittest.TestCase):
    def test_bigram(self): self.assertEqual(char_ngrams("abc", 2), ["ab", "bc"])
    def test_unigram(self): self.assertEqual(char_ngrams("abc", 1), ["a", "b", "c"])
    def test_short(self): self.assertEqual(char_ngrams("a", 2), [])
    def test_exact(self): self.assertEqual(char_ngrams("ab", 2), ["ab"])
    def test_invalid(self):
        with self.assertRaises(ValueError): char_ngrams("abc", 0)
    def test_long(self): self.assertEqual(len(char_ngrams("abcdef", 3)), 4)
    def test_determinism(self): self.assertEqual(char_ngrams("xyz", 2), char_ngrams("xyz", 2))
    def test_trigram(self): self.assertEqual(char_ngrams("abcd", 3), ["abc", "bcd"])
    def test_same(self): self.assertEqual(char_ngrams("aa", 1), ["a", "a"])
    def test_empty(self): self.assertEqual(char_ngrams("", 2), [])

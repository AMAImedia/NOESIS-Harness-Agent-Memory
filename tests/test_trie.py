import unittest
from noesis_harness.trie import Trie

class TestTrie(unittest.TestCase):
    def test_insert_has(self): t = Trie(); t.insert("cat"); self.assertTrue(t.has("cat")); self.assertFalse(t.has("dog"))
    def test_prefix(self): t = Trie(); t.insert("cat"); t.insert("car"); self.assertTrue(t.starts_with("ca")); self.assertFalse(t.starts_with("do"))
    def test_partial_no_word(self): t = Trie(); t.insert("cats"); self.assertFalse(t.has("cat"))
    def test_count(self): t = Trie(); t.insert("cat"); t.insert("car"); t.insert("dog"); self.assertEqual(t.count(), 3)
    def test_empty(self): t = Trie(); self.assertEqual(t.count(), 0); self.assertFalse(t.has("a"))
    def test_overlap(self): t = Trie(); t.insert("a"); t.insert("ab"); self.assertTrue(t.has("a")); self.assertTrue(t.has("ab")); self.assertEqual(t.count(), 2)
    def test_missing_prefix(self): t = Trie(); t.insert("abc"); self.assertFalse(t.starts_with("z"))
    def test_determinism(self): a = Trie(); b = Trie(); a.insert("x"); b.insert("x"); self.assertEqual(a.has("x"), b.has("x"))
    def test_many(self):
        t = Trie()
        for w in ["a", "ab", "abc", "abcd", "abcde"]: t.insert(w)
        self.assertEqual(t.count(), 5)
    def test_no_word_in_substring(self): t = Trie(); t.insert("hello"); self.assertFalse(t.has("hell")); self.assertTrue(t.starts_with("hell"))

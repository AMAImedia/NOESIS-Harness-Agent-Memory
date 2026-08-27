"""Tests for noesis_harness.text_norm.

Covers whitespace collapse, ASCII folding, tokenization, truncation boundary
behavior, empty input, and determinism. Stdlib only.
"""

import unittest

from noesis_harness import text_norm


class TestNormalizeWs(unittest.TestCase):

    def test_collapse_internal_runs(self):
        self.assertEqual(text_norm.normalize_ws("a   b\t\tc"), "a b c")

    def test_collapse_newlines_and_tabs(self):
        self.assertEqual(text_norm.normalize_ws("x\n\ny\r\nz"), "x y z")

    def test_strip_ends(self):
        self.assertEqual(text_norm.normalize_ws("   hello   "), "hello")

    def test_empty_and_whitespace(self):
        self.assertEqual(text_norm.normalize_ws(""), "")
        self.assertEqual(text_norm.normalize_ws("   \n\t  "), "")

    def test_none_raises(self):
        with self.assertRaises(TypeError):
            text_norm.normalize_ws(None)


class TestToAsciiFold(unittest.TestCase):

    def test_accent_folding(self):
        self.assertEqual(text_norm.to_ascii_fold("café"), "cafe")
        self.assertEqual(text_norm.to_ascii_fold("naïve"), "naive")

    def test_ligature_nfkc(self):
        self.assertEqual(text_norm.to_ascii_fold("ﬁsh"), "fish")

    def test_fullwidth_to_ascii(self):
        self.assertEqual(text_norm.to_ascii_fold("ＡＢＣ１２３"), "ABC123")

    def test_non_foldable_dropped(self):
        self.assertEqual(text_norm.to_ascii_fold("日本語"), "")

    def test_empty(self):
        self.assertEqual(text_norm.to_ascii_fold(""), "")


class TestTokenize(unittest.TestCase):

    def test_lowercase_alnum(self):
        self.assertEqual(
            text_norm.tokenize("Hello, World!"), ["hello", "world"]
        )

    def test_accents_folded_before_tokenize(self):
        self.assertEqual(text_norm.tokenize("Café Crème"), ["cafe", "creme"])

    def test_punctuation_separates(self):
        self.assertEqual(
            text_norm.tokenize("a.b-c_d e"), ["a", "b", "c", "d", "e"]
        )

    def test_empty_and_whitespace(self):
        self.assertEqual(text_norm.tokenize(""), [])
        self.assertEqual(text_norm.tokenize("   "), [])

    def test_numbers_kept(self):
        self.assertEqual(text_norm.tokenize("v2 and 42"), ["v2", "and", "42"])


class TestTruncate(unittest.TestCase):

    def test_within_budget_unchanged(self):
        self.assertEqual(text_norm.truncate("abc", 5), "abc")

    def test_boundary_exact(self):
        self.assertEqual(text_norm.truncate("abcd", 4), "abcd")

    def test_over_budget_truncated(self):
        self.assertEqual(text_norm.truncate("abcdef", 3), "abc")

    def test_none_or_negative_returns_original(self):
        self.assertEqual(text_norm.truncate("abc", None), "abc")
        self.assertEqual(text_norm.truncate("abc", -1), "abc")

    def test_empty(self):
        self.assertEqual(text_norm.truncate("", 0), "")

    def test_none_raises(self):
        with self.assertRaises(TypeError):
            text_norm.truncate(None, 3)


class TestDeterminism(unittest.TestCase):

    def test_repeatable_outputs(self):
        samples = ["  Héllo   Wörld  ", "ﬁsh & CHIPS", "ＡＢ  café"]
        for s in samples:
            self.assertEqual(text_norm.normalize_ws(s), text_norm.normalize_ws(s))
            self.assertEqual(text_norm.to_ascii_fold(s), text_norm.to_ascii_fold(s))
            self.assertEqual(text_norm.tokenize(s), text_norm.tokenize(s))

    def test_truncate_idempotent(self):
        s = "a" * 20
        once = text_norm.truncate(s, 10)
        self.assertEqual(text_norm.truncate(once, 10), once)


if __name__ == "__main__":
    unittest.main()

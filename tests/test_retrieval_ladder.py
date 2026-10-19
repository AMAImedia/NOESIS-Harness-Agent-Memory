"""Tests for noesis_harness.retrieval_ladder.

Covers tokenization, the five-tier retrieval ladder (each tier reachable and
ordered), BM25/freshness scoring, Damerau-Levenshtein distance with early exit,
UTF-8 byte-budget trimming, tie-breaking, relevance-tail bounding, and
determinism. Stdlib only.
"""

import unittest

from noesis_harness.retrieval_ladder import (
    Hit,
    SearchTier,
    bm25_score,
    damerau_levenshtein,
    freshness_decay,
    rank_with_relevance_tail,
    search_tiered,
    tokenize,
    trim_to_budget,
)


class TestTokenize(unittest.TestCase):

    def test_lowercase_and_split(self):
        self.assertEqual(
            tokenize("Hello, world! Foo-bar Baz2"),
            ["hello", "world", "foo", "bar", "baz2"],
        )

    def test_dedup_first_seen_order(self):
        self.assertEqual(tokenize("beta alpha beta alpha gamma"), ["beta", "alpha", "gamma"])

    def test_empty_and_punctuation_only(self):
        self.assertEqual(tokenize(""), [])
        self.assertEqual(tokenize("!!! ,,, ---"), [])

    def test_underscore_splits_tokens(self):
        self.assertEqual(tokenize("foo_bar"), ["foo", "bar"])


class TestTierLadder(unittest.TestCase):

    def test_exact_beats_prefix_substring_fuzzy(self):
        docs = {
            "a": "alpha beta",
            "b": "alphabet soup",
            "c": "alpah",
        }
        hits = search_tiered(docs, "alpha beta")
        self.assertEqual([hit.doc_id for hit in hits], ["a"])
        self.assertTrue(all(hit.tier is SearchTier.EXACT for hit in hits))

    def test_prefix_tier_reachable(self):
        docs = {"p1": "alphabet soup", "p2": "alphanumeric code"}
        hits = search_tiered(docs, "alpha")
        self.assertEqual(sorted(hit.doc_id for hit in hits), ["p1", "p2"])
        self.assertTrue(all(hit.tier is SearchTier.PREFIX for hit in hits))

    def test_substring_tier_reachable(self):
        docs = {"s1": "alphabet soup"}
        hits = search_tiered(docs, "pha")
        self.assertEqual([hit.doc_id for hit in hits], ["s1"])
        self.assertTrue(all(hit.tier is SearchTier.SUBSTRING for hit in hits))

    def test_fuzzy_tier_reachable(self):
        docs = {"f1": "alpah"}
        hits = search_tiered(docs, "alpha")
        self.assertEqual([hit.doc_id for hit in hits], ["f1"])
        self.assertTrue(all(hit.tier is SearchTier.FUZZY for hit in hits))

    def test_relevance_tier_reachable(self):
        docs = {"r1": "alpha gamma", "r2": "beta omega"}
        hits = search_tiered(docs, "alpha beta")
        self.assertEqual(sorted(hit.doc_id for hit in hits), ["r1", "r2"])
        self.assertTrue(all(hit.tier is SearchTier.RELEVANCE for hit in hits))

    def test_empty_query_returns_empty(self):
        docs = {"a": "alpha beta"}
        self.assertEqual(search_tiered(docs, ""), [])
        self.assertEqual(search_tiered(docs, "   !!!  "), [])
        self.assertEqual(search_tiered({}, "alpha"), [])

    def test_limit_applies(self):
        docs = {"a": "alpha", "b": "alpha", "c": "alpha"}
        hits = search_tiered(docs, "alpha", limit=2)
        self.assertEqual(len(hits), 2)
        self.assertEqual([hit.doc_id for hit in hits], ["a", "b"])

    def test_tie_break_by_doc_id(self):
        docs = {"b": "alpha beta", "a": "alpha beta", "c": "alpha beta"}
        hits = search_tiered(docs, "alpha beta")
        self.assertEqual([hit.doc_id for hit in hits], ["a", "b", "c"])

    def test_determinism_across_two_runs(self):
        docs = {
            "a": "alpha beta gamma",
            "b": "alphabet soup",
            "c": "alpah",
            "d": "gamma delta",
        }
        first = search_tiered(docs, "alpha beta")
        second = search_tiered(docs, "alpha beta")
        self.assertEqual(first, second)


class TestScoring(unittest.TestCase):

    def test_bm25_increases_with_frequency_and_idf(self):
        low = bm25_score(1, 5, 10, 10.0, 10)
        high = bm25_score(3, 2, 10, 10.0, 10)
        self.assertGreater(high, low)
        self.assertEqual(bm25_score(0, 2, 10, 10.0, 10), 0.0)
        self.assertEqual(bm25_score(2, 2, 10, 10.0, 0), 0.0)

    def test_freshness_bounds_and_monotonic(self):
        self.assertEqual(freshness_decay(0.0), 1.0)
        self.assertEqual(freshness_decay(-5.0), 1.0)
        self.assertGreater(freshness_decay(0.0), freshness_decay(1.0))
        self.assertGreater(freshness_decay(1.0), freshness_decay(365.0))
        for age in (0.0, 1.0, 10.0, 1000.0):
            value = freshness_decay(age)
            self.assertGreater(value, 0.5)
            self.assertLessEqual(value, 1.0)


class TestDamerauLevenshtein(unittest.TestCase):

    def test_basic_operations(self):
        self.assertEqual(damerau_levenshtein("cat", "cut"), 1)
        self.assertEqual(damerau_levenshtein("cat", "cats"), 1)
        self.assertEqual(damerau_levenshtein("", "abc"), 3)
        self.assertEqual(damerau_levenshtein("kitten", "sitting"), 3)

    def test_transposition_counts_one(self):
        self.assertEqual(damerau_levenshtein("ab", "ba"), 1)
        self.assertEqual(damerau_levenshtein("alpah", "alpha"), 1)

    def test_early_exit_returns_bounded_sentinel(self):
        self.assertGreater(damerau_levenshtein("abcdef", "uvwxyz", 1), 1)
        self.assertEqual(damerau_levenshtein("abcdef", "uvwxyz", 1), 2)
        self.assertGreater(damerau_levenshtein("alpha", "beta", 0), 0)


class TestTrimToBudget(unittest.TestCase):

    def test_ascii_trim_with_marker(self):
        result = trim_to_budget("hello wonderful world", 8, marker="...")
        self.assertEqual(result, "hello...")
        self.assertLessEqual(len(result.encode("utf-8")), 8)

    def test_returns_unchanged_when_fits(self):
        self.assertEqual(trim_to_budget("hi", 100), "hi")

    def test_multibyte_cyrillic_stays_within_budget(self):
        result = trim_to_budget("привет мир", 15, marker="[...]")
        self.assertLessEqual(len(result.encode("utf-8")), 15)
        self.assertNotIn("\ufffd", result)
        self.assertTrue(result.endswith("[...]"))

    def test_multibyte_cjk_never_splits_codepoint(self):
        result = trim_to_budget("你好世界再见", 10, marker="[...]")
        self.assertLessEqual(len(result.encode("utf-8")), 10)
        self.assertNotIn("\ufffd", result)
        result.encode("utf-8").decode("utf-8")

    def test_marker_larger_than_budget(self):
        result = trim_to_budget("привет", 2, marker=".....")
        self.assertLessEqual(len(result.encode("utf-8")), 2)
        self.assertNotIn("\ufffd", result)

    def test_tiny_and_zero_budgets_do_not_raise(self):
        for budget in (0, 1, 2, 3):
            result = trim_to_budget("привет мир 你好", budget)
            self.assertLessEqual(len(result.encode("utf-8")), budget)


class TestRelevanceTail(unittest.TestCase):

    def test_exact_stays_strictly_ahead(self):
        hits = [Hit("a", 5.0, SearchTier.EXACT), Hit("c", 100.0, SearchTier.FUZZY)]
        docs = {"a": "alpha beta", "c": "alpha gamma"}
        result = rank_with_relevance_tail(hits, docs, "alpha beta", lead=0.1)
        self.assertEqual(result[0].doc_id, "a")
        self.assertEqual(result[0].tier, SearchTier.EXACT)
        for hit in result:
            if hit.tier is not SearchTier.EXACT:
                self.assertLessEqual(hit.score, 5.0 - 0.1 + 1e-9)

    def test_attaches_relevance_tail(self):
        hits = [Hit("a", 5.0, SearchTier.EXACT)]
        docs = {"a": "alpha beta", "d": "alpha only"}
        result = rank_with_relevance_tail(hits, docs, "alpha beta")
        self.assertEqual(result[0].doc_id, "a")
        tail = [hit for hit in result if hit.doc_id == "d"]
        self.assertEqual(len(tail), 1)
        self.assertIs(tail[0].tier, SearchTier.RELEVANCE)
        self.assertLess(tail[0].score, 5.0)

    def test_no_exact_hits_keeps_scores(self):
        hits = [Hit("c", 3.0, SearchTier.PREFIX)]
        result = rank_with_relevance_tail(hits, {"c": "catalog"}, "cat")
        self.assertEqual(result[0].doc_id, "c")
        self.assertEqual(result[0].score, 3.0)


if __name__ == "__main__":
    unittest.main()

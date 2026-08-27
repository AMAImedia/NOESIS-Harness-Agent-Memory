"""Tests for noesis_harness/relevance_rank (stdlib-only BM25-ish ranker)."""

from __future__ import annotations

import unittest

from noesis_harness.relevance_rank import rank


class TestRelevanceRank(unittest.TestCase):
    def _docs(self):
        return [
            {"id": "a", "text": "the quick brown fox jumps over the lazy dog"},
            {"id": "b", "text": "a lazy dog sleeps all day near the warm fire"},
            {"id": "c", "text": "quantum physics explains the strange behavior of atoms"},
            {"id": "d", "text": "the brown fox is quick and the dog is lazy"},
        ]

    def test_ranking_order_favors_term_overlap(self):
        result = rank("warm fire sleeps", self._docs(), top_k=4)
        self.assertEqual(result[0], "b")

    def test_query_unique_term_ranks_specific_doc_first(self):
        result = rank("quantum physics atoms", self._docs(), top_k=4)
        self.assertEqual(result[0], "c")

    def test_top_k_truncation(self):
        result = rank("the", self._docs(), top_k=2)
        self.assertEqual(len(result), 2)
        self.assertEqual(set(result), {"a", "d"})

    def test_top_k_larger_than_corpus_returns_all(self):
        result = rank("the", self._docs(), top_k=100)
        self.assertEqual(len(result), 4)

    def test_empty_docs_returns_empty(self):
        self.assertEqual(rank("anything", [], top_k=5), [])

    def test_top_k_zero_returns_empty(self):
        self.assertEqual(rank("anything", self._docs(), top_k=0), [])

    def test_query_no_match_returns_empty(self):
        result = rank("zzz_nonexistent_token", self._docs(), top_k=4)
        self.assertEqual(result, [])

    def test_empty_query_returns_empty(self):
        self.assertEqual(rank("", self._docs(), top_k=4), [])

    def test_determinism_identical_inputs(self):
        docs = self._docs()
        first = rank("brown fox quick", docs, top_k=4)
        second = rank("brown fox quick", docs, top_k=4)
        self.assertEqual(first, second)

    def test_determinism_across_reordered_call_objects(self):
        a = rank("the lazy dog", self._docs(), top_k=4)
        b = rank("the lazy dog", list(self._docs()), top_k=4)
        self.assertEqual(a, b)

    def test_tie_handling_preserves_original_order(self):
        docs = [
            {"id": "x", "text": "alpha beta gamma"},
            {"id": "y", "text": "alpha beta gamma"},
            {"id": "z", "text": "alpha beta gamma"},
        ]
        result = rank("alpha beta gamma", docs, top_k=3)
        self.assertEqual(result, ["x", "y", "z"])

    def test_duplicate_ids_ranked_independently(self):
        docs = [
            {"id": "dup", "text": "unique strawberry fields forever"},
            {"id": "other", "text": "completely unrelated content here"},
            {"id": "dup", "text": "unique strawberry fields again"},
        ]
        result = rank("strawberry fields", docs, top_k=3)
        self.assertEqual(result, ["dup", "dup"])

    def test_unicode_text_tokenized_gracefully(self):
        docs = [
            {"id": "u1", "text": "café résumé naïve über fox"},
            {"id": "u2", "text": "the lazy brown dog jumps"},
        ]
        result = rank("café résumé", docs, top_k=2)
        self.assertEqual(result[0], "u1")

    def test_unicode_only_query_no_match_returns_empty(self):
        docs = [{"id": "u1", "text": "plain ascii words only"}]
        result = rank("日本語", docs, top_k=2)
        self.assertEqual(result, [])

    def test_no_mutation_of_input_docs(self):
        docs = self._docs()
        snapshot = [dict(d) for d in docs]
        rank("lazy dog", docs, top_k=4)
        self.assertEqual([dict(d) for d in docs], snapshot)


if __name__ == "__main__":
    unittest.main()

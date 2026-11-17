"""tests/test_inverted_index.py

Unit tests for noesis_harness.inverted_index: tokenization, ASCII/FNV prefix
sharding, delta-varint postings, BM25 scoring, search ranking and JSON
persistence.

Stdlib only. Run: python -m unittest tests.test_inverted_index -q
"""

import os
import re
import tempfile
import unittest

from noesis_harness.inverted_index import (
    STOPWORDS,
    InvertedIndex,
    bm25_score,
    bucket,
    decode_postings,
    encode_postings,
    tokenize,
)

_HEX2 = re.compile(r"^[0-9a-f]{2}$")


class TestTokenize(unittest.TestCase):
    def test_tokenize_lowercases_and_splits_on_non_alnum(self):
        self.assertEqual(
            tokenize("Hello, WORLD! foo-bar_baz"),
            ["hello", "world", "foo", "bar", "baz"],
        )

    def test_tokenize_drops_stopwords(self):
        self.assertIn("the", STOPWORDS)
        self.assertEqual(tokenize("the quick brown fox"), ["quick", "brown", "fox"])

    def test_tokenize_drops_single_characters(self):
        self.assertEqual(tokenize("a i x to go"), ["go"])

    def test_tokenize_preserves_first_seen_order_and_dedupes(self):
        self.assertEqual(
            tokenize("beta alpha beta gamma alpha"),
            ["beta", "alpha", "gamma"],
        )

    def test_tokenize_empty_and_whitespace(self):
        self.assertEqual(tokenize(""), [])
        self.assertEqual(tokenize("   ---   "), [])


class TestBucket(unittest.TestCase):
    def test_bucket_ascii_prefix_lowercased(self):
        self.assertEqual(bucket("Hello"), "he")
        self.assertEqual(bucket("WORLD"), "wo")
        self.assertEqual(bucket("a1b2"), "a1")

    def test_bucket_hash_fallback_is_two_hex_digits(self):
        for token in ("1", "x", "9", "\u00e9toile"):
            key = bucket(token)
            self.assertTrue(_HEX2.match(key), "bad bucket %r for %r" % (key, token))

    def test_bucket_is_deterministic(self):
        self.assertEqual(bucket("1"), bucket("1"))
        self.assertEqual(bucket("\u00e9"), bucket("\u00e9"))


class TestPostingsCodec(unittest.TestCase):
    def test_encode_decode_roundtrip_sorted(self):
        postings = [(2, 40), (0, 5), (1, 17)]
        encoded = encode_postings(postings)
        decoded = decode_postings(encoded)
        self.assertEqual(decoded, [(0, 5), (1, 17), (2, 40)])

    def test_encode_sorts_and_dedupes(self):
        encoded = encode_postings([(1, 4), (1, 4), (0, 9), (0, 2)])
        self.assertEqual(decode_postings(encoded), [(0, 2), (0, 9), (1, 4)])

    def test_negative_offset_deltas_roundtrip(self):
        postings = [(0, 10), (0, 3), (1, 1)]
        decoded = decode_postings(encode_postings(postings))
        self.assertEqual(decoded, [(0, 3), (0, 10), (1, 1)])

    def test_empty_input_roundtrip(self):
        self.assertEqual(encode_postings([]), b"")
        self.assertEqual(decode_postings(b""), [])

    def test_truncated_stream_raises(self):
        encoded = encode_postings([(0, 5), (1, 9)])
        with self.assertRaises(ValueError):
            decode_postings(encoded[:-1])


class TestInvertedIndex(unittest.TestCase):
    def test_add_returns_ordinal_and_num_docs(self):
        index = InvertedIndex()
        self.assertEqual(index.add("d1", "alpha beta"), 0)
        self.assertEqual(index.add("d2", "gamma"), 1)
        self.assertEqual(index.add("d3", "delta"), 2)
        self.assertEqual(index.num_docs(), 3)

    def test_add_duplicate_doc_id_is_idempotent(self):
        index = InvertedIndex()
        first = index.add("d1", "alpha beta")
        second = index.add("d1", "completely different")
        self.assertEqual(first, second)
        self.assertEqual(index.num_docs(), 1)
        self.assertEqual(index.doc_text("d1"), "alpha beta")

    def test_postings_and_doc_frequency(self):
        index = InvertedIndex()
        index.add("d1", "alpha alpha beta")
        index.add("d2", "alpha")
        index.add("d3", "beta")
        self.assertEqual(index.postings("alpha"), [(0, 2), (1, 1)])
        self.assertEqual(index.postings("beta"), [(0, 1), (2, 1)])
        self.assertEqual(index.doc_frequency("alpha"), 2)
        self.assertEqual(index.doc_frequency("beta"), 2)
        self.assertEqual(index.postings("missing"), [])
        self.assertEqual(index.doc_frequency("missing"), 0)

    def test_search_ranks_all_terms_above_partial(self):
        index = InvertedIndex()
        index.add("both", "alpha beta gamma")
        index.add("partial", "alpha delta epsilon")
        results = index.search("alpha beta")
        self.assertEqual([doc for doc, _ in results], ["both", "partial"])
        self.assertGreater(results[0][1], results[1][1])

    def test_search_empty_query_returns_empty(self):
        index = InvertedIndex()
        index.add("d1", "alpha beta")
        self.assertEqual(index.search(""), [])
        self.assertEqual(index.search("the and of"), [])
        self.assertEqual(index.search("alpha", limit=0), [])

    def test_search_tie_break_by_doc_id_ascending(self):
        index = InvertedIndex()
        index.add("b", "alpha beta")
        index.add("a", "alpha beta")
        results = index.search("alpha beta")
        self.assertEqual([doc for doc, _ in results], ["a", "b"])
        self.assertAlmostEqual(results[0][1], results[1][1])

    def test_buckets_counts_distinct_tokens(self):
        index = InvertedIndex()
        index.add("d1", "hello help world")
        counts = index.buckets()
        self.assertEqual(counts.get("he"), 2)
        self.assertEqual(counts.get("wo"), 1)

    def test_determinism_across_two_identical_builds(self):
        docs = [("d1", "alpha beta gamma"), ("d2", "beta delta"), ("d3", "alpha")]

        def build():
            idx = InvertedIndex()
            for doc_id, text in docs:
                idx.add(doc_id, text)
            return idx

        one = build()
        two = build()
        self.assertEqual(one.search("alpha beta"), two.search("alpha beta"))
        self.assertEqual(one.buckets(), two.buckets())
        self.assertEqual(one.num_docs(), two.num_docs())
        self.assertEqual(
            encode_postings(one.postings("beta")),
            encode_postings(two.postings("beta")),
        )


class TestBM25(unittest.TestCase):
    def test_bm25_positive_for_valid_inputs(self):
        score = bm25_score(tf=2, df=1, doc_len=5, avg_doc_len=5.0, n_docs=3)
        self.assertGreater(score, 0.0)

    def test_bm25_zero_denominators_return_zero(self):
        self.assertEqual(
            bm25_score(tf=0, df=1, doc_len=5, avg_doc_len=5.0, n_docs=3), 0.0
        )
        self.assertEqual(
            bm25_score(tf=1, df=0, doc_len=5, avg_doc_len=5.0, n_docs=3), 0.0
        )
        self.assertEqual(
            bm25_score(tf=1, df=1, doc_len=5, avg_doc_len=0.0, n_docs=3), 0.0
        )
        self.assertEqual(
            bm25_score(tf=1, df=1, doc_len=5, avg_doc_len=5.0, n_docs=0), 0.0
        )


class TestPersistence(unittest.TestCase):
    def test_save_load_roundtrip_preserves_search(self):
        index = InvertedIndex()
        index.add("d1", "alpha beta gamma")
        index.add("d2", "beta delta")
        index.add("d3", "alpha")
        before = index.search("alpha beta", limit=5)

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "index.json")
            index.save(path)
            self.assertTrue(os.path.exists(path))
            loaded = InvertedIndex.load(path)

        self.assertEqual(loaded.num_docs(), index.num_docs())
        self.assertEqual(loaded.search("alpha beta", limit=5), before)
        self.assertEqual(loaded.buckets(), index.buckets())
        self.assertEqual(loaded.doc_text("d1"), "alpha beta gamma")

    def test_load_rejects_invalid_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("[1, 2, 3]")
            with self.assertRaises(ValueError):
                InvertedIndex.load(path)


if __name__ == "__main__":
    unittest.main()

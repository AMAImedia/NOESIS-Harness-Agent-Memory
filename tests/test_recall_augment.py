"""Tests for noesis_harness/recall_augment.py

Covers deterministic scoring, top_k truncation, empty/missing logs, recency
ordering, and idempotent read-only behavior. Stdlib only.
"""

import os
import tempfile
import unittest

from noesis_harness import event_store
from noesis_harness import recall_augment


def _write_log(path, records):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(rec + "\n")


def _append_events(path, items):
    """items: list of (event_type, payload). Returns seq order as written."""
    store = event_store.EventStore(path)
    for etype, payload in items:
        store.append(etype, payload)


class RecallAugmentTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="recall_test_")
        self.log = os.path.join(self.tmp, "events.jsonl")

    def _sample_log(self):
        _append_events(
            self.log,
            [
                ("note", {"text": "deploy the blue service to production"}),
                ("note", {"text": "rollback the red service after the incident"}),
                ("task", {"text": "the blue service handles user authentication"}),
                ("note", {"text": "unrelated invoice total is forty two dollars"}),
            ],
        )

    def test_ranking_prefers_term_overlap(self):
        self._sample_log()
        ranked = recall_augment.rank_events("blue service production", self.log, top_k=8)
        self.assertGreaterEqual(len(ranked), 3)
        top = ranked[0]
        self.assertEqual(top["type"], "note")
        self.assertIn("blue service", top["snippet"])
        # Highest score must be the strongest overlap event.
        self.assertGreaterEqual(top["score"], ranked[-1]["score"])

    def test_score_is_deterministic(self):
        self._sample_log()
        a = recall_augment.rank_events("blue service production", self.log)
        b = recall_augment.rank_events("blue service production", self.log)
        self.assertEqual(a, b)
        # Scores are stable floats.
        self.assertEqual([r["score"] for r in a], [r["score"] for r in b])

    def test_top_k_truncation(self):
        self._sample_log()
        ranked = recall_augment.rank_events("service", self.log, top_k=2)
        self.assertEqual(len(ranked), 2)
        # Sorted descending by score.
        self.assertGreaterEqual(ranked[0]["score"], ranked[1]["score"])

    def test_top_k_zero_returns_empty(self):
        self._sample_log()
        ranked = recall_augment.rank_events("service", self.log, top_k=0)
        self.assertEqual(ranked, [])

    def test_missing_log_returns_empty_list(self):
        missing = os.path.join(self.tmp, "does_not_exist.jsonl")
        ranked = recall_augment.rank_events("anything", missing, top_k=8)
        self.assertEqual(ranked, [])

    def test_empty_log_returns_empty_list(self):
        _write_log(self.log, [])
        ranked = recall_augment.rank_events("anything", self.log, top_k=8)
        self.assertEqual(ranked, [])

    def test_build_context_empty_for_missing_log(self):
        missing = os.path.join(self.tmp, "nope.jsonl")
        ctx = recall_augment.build_augmented_context("x", missing)
        self.assertEqual(ctx, "")

    def test_build_context_includes_snippets(self):
        self._sample_log()
        ctx = recall_augment.build_augmented_context("blue service", self.log, top_k=8)
        self.assertIn("## Recalled context", ctx)
        self.assertIn("blue service", ctx)
        self.assertIn("```", ctx)

    def test_build_context_is_markdownish_and_truncated(self):
        long_text = {"text": "blue " + ("x" * 500)}
        _append_events(self.log, [("note", long_text)])
        ctx = recall_augment.build_augmented_context("blue", self.log, top_k=1)
        self.assertIn("...", ctx)
        self.assertLessEqual(ctx.count("\n"), 12)

    def test_recency_breaks_ties(self):
        # Events with identical query-token overlap but different seq.
        # A unique id field keeps EventStore from deduping identical payloads.
        _append_events(
            self.log,
            [
                ("note", {"text": "alpha beta gamma", "id": 1}),
                ("note", {"text": "alpha beta gamma", "id": 2}),
                ("note", {"text": "alpha beta gamma", "id": 3}),
            ],
        )
        ranked = recall_augment.rank_events("alpha beta gamma", self.log, top_k=8)
        seqs = [r["seq"] for r in ranked]
        self.assertEqual(seqs, [3, 2, 1])

    def test_recency_bonus_when_overlap_tied(self):
        # Same overlap fraction, later seq should outrank earlier.
        _append_events(
            self.log,
            [
                ("note", {"text": "token panda", "id": "a"}),
                ("task", {"z": "token panda", "id": "b"}),
            ],
        )
        ranked = recall_augment.rank_events("token panda", self.log, top_k=8)
        self.assertEqual(len(ranked), 2)
        self.assertGreater(ranked[0]["seq"], ranked[1]["seq"])

    def test_log_not_mutated(self):
        self._sample_log()
        with open(self.log, "rb") as fh:
            before = fh.read()
        recall_augment.rank_events("blue", self.log)
        recall_augment.build_augmented_context("blue", self.log)
        with open(self.log, "rb") as fh:
            after = fh.read()
        self.assertEqual(before, after)

    def test_result_keys_complete(self):
        self._sample_log()
        ranked = recall_augment.rank_events("blue service", self.log, top_k=1)
        self.assertEqual(len(ranked), 1)
        item = ranked[0]
        self.assertIn("seq", item)
        self.assertIn("event_id", item)
        self.assertIn("type", item)
        self.assertIn("score", item)
        self.assertIn("snippet", item)
        self.assertIsInstance(item["score"], float)

    def test_determinism_across_instances(self):
        # A fresh EventStore + re-rank should reproduce identical output.
        self._sample_log()
        first = recall_augment.rank_events("rollback incident red", self.log)
        second = recall_augment.rank_events("rollback incident red", self.log)
        self.assertEqual(first, second)
        self.assertEqual([r["event_id"] for r in first],
                         [r["event_id"] for r in second])

    def test_zero_query_yields_zero_scores(self):
        self._sample_log()
        ranked = recall_augment.rank_events("", self.log, top_k=8)
        self.assertTrue(all(r["score"] == 0.0 for r in ranked))
        ctx = recall_augment.build_augmented_context("", self.log, top_k=8)
        self.assertEqual(ctx, "")


if __name__ == "__main__":
    unittest.main()

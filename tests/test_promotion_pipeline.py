"""Tests for noesis_harness.promotion_pipeline (Track B -- governed self-learning).

These tests assert governance behaviour only: a candidate is marked "promoted"
in the append-only journal if and only if the deterministic holdout gate in
``learning_promotion`` passes. They never execute or evaluate model output.
"""

import json
import os
import tempfile
import unittest

from noesis_harness.learning_journal import LearningJournal
from noesis_harness.promotion_pipeline import evaluate


def _candidate(cases, *, scope="project:demo", candidate_id="cand-1", evaluator_version="v1"):
    return {
        "scope": scope,
        "candidate_id": candidate_id,
        "evaluator_version": evaluator_version,
        "cases": cases,
    }


def _passing_cases(n=3):
    return [{"case_id": "c%d" % i, "passed": True, "leaked": False} for i in range(n)]


def _failing_cases():
    return [
        {"case_id": "c0", "passed": True, "leaked": False},
        {"case_id": "c1", "passed": False, "leaked": False},
    ]


def _leaked_cases():
    return [{"case_id": "c0", "passed": True, "leaked": True}]


class PromotionPipelineTests(unittest.TestCase):
    def setUp(self):
        self.journal_fd, self.journal_path = tempfile.mkstemp(suffix=".jsonl")
        os.close(self.journal_fd)
        self.promo_fd, self.promo_path = tempfile.mkstemp(suffix=".jsonl")
        os.close(self.promo_fd)

    def tearDown(self):
        for path in (self.journal_path, self.promo_path):
            if os.path.exists(path):
                os.remove(path)

    def test_promoted_only_when_holdout_passes(self):
        ok = evaluate(_candidate(_passing_cases()), self.journal_path)
        self.assertTrue(ok["promoted"])
        self.assertTrue(ok["holdout_passed"])

        j2_fd, journal2 = tempfile.mkstemp(suffix=".jsonl")
        os.close(j2_fd)
        try:
            bad = evaluate(_candidate(_failing_cases()), journal2)
            self.assertFalse(bad["promoted"])
            self.assertFalse(bad["holdout_passed"])
        finally:
            os.remove(journal2)

    def test_recorded_entry_present(self):
        result = evaluate(_candidate(_passing_cases()), self.journal_path)
        journal = LearningJournal(self.journal_path)
        entries = journal.replay()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["entry_id"], result["entry_id"])
        self.assertEqual(entries[0]["action"], "promote")
        self.assertEqual(entries[0]["payload"]["decision"], "promoted")

    def test_recorded_entry_replayable(self):
        evaluate(_candidate(_passing_cases()), self.journal_path)
        first = LearningJournal(self.journal_path).replay()
        digest1 = LearningJournal(self.journal_path).holdout_summary()["replay_digest"]
        # Re-open from disk: replay must be identical and reproducible.
        second = LearningJournal(self.journal_path).replay()
        digest2 = LearningJournal(self.journal_path).holdout_summary()["replay_digest"]
        self.assertEqual([e["entry_id"] for e in first], [e["entry_id"] for e in second])
        self.assertEqual(digest1, digest2)

    def test_idempotent_record(self):
        evaluate(_candidate(_passing_cases()), self.journal_path)
        count_before = len(LearningJournal(self.journal_path).replay())
        # Same candidate again: journal must not grow (no duplicate promotion).
        evaluate(_candidate(_passing_cases()), self.journal_path)
        count_after = len(LearningJournal(self.journal_path).replay())
        self.assertEqual(count_before, 1)
        self.assertEqual(count_after, 1)

    def test_fails_closed_on_bad_candidate(self):
        bad_inputs = [
            None,
            "not-a-dict",
            {},
            {"scope": "", "candidate_id": "x", "evaluator_version": "v1", "cases": [{"case_id": "c0"}]},
            {"scope": "s", "candidate_id": "", "evaluator_version": "v1", "cases": [{"case_id": "c0"}]},
            {"scope": "s", "candidate_id": "x", "evaluator_version": "", "cases": [{"case_id": "c0"}]},
            {"scope": "s", "candidate_id": "x", "evaluator_version": "v1", "cases": []},
            {"scope": "s", "candidate_id": "x", "evaluator_version": "v1", "cases": [{"case_id": ""}]},
        ]
        for bad in bad_inputs:
            with self.subTest(candidate=bad):
                with self.assertRaises(ValueError):
                    evaluate(bad, self.journal_path)
        # No promotion entry should have been written.
        self.assertEqual(len(LearningJournal(self.journal_path).replay()), 0)

    def test_holdout_detail_shape(self):
        result = evaluate(_candidate(_passing_cases(4)), self.journal_path)
        holdout = result["holdout"]
        self.assertEqual(set(holdout.keys()), {
            "total_cases", "passed_cases", "leaked_cases", "status", "holdout_digest",
        })
        self.assertEqual(holdout["total_cases"], 4)
        self.assertEqual(holdout["passed_cases"], 4)
        self.assertEqual(holdout["leaked_cases"], 0)
        self.assertEqual(holdout["status"], "passed")
        self.assertEqual(len(holdout["holdout_digest"]), 64)

    def test_no_event_log_mutation(self):
        # Pre-seed the journal with an unrelated governance entry.
        seed = LearningJournal(self.journal_path)
        seed_id = seed.record(scope="project:seed", action="record", payload={"note": "preexisting"})
        # Run the pipeline; the seeded entry must remain intact and unaltered.
        evaluate(_candidate(_passing_cases()), self.journal_path)
        entries = LearningJournal(self.journal_path).replay()
        self.assertEqual(len(entries), 2)
        seeded = [e for e in entries if e["entry_id"] == seed_id][0]
        self.assertEqual(seeded["payload"], {"note": "preexisting"})
        self.assertEqual(seeded["action"], "record")

    def test_reject_action_recorded_when_holdout_fails(self):
        result = evaluate(_candidate(_failing_cases()), self.journal_path)
        self.assertFalse(result["promoted"])
        entries = LearningJournal(self.journal_path).replay()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "reject")
        self.assertEqual(entries[0]["payload"]["decision"], "rejected")

    def test_promote_action_recorded_when_holdout_passes(self):
        evaluate(_candidate(_passing_cases()), self.journal_path)
        entries = LearningJournal(self.journal_path).replay()
        self.assertEqual(entries[0]["action"], "promote")

    def test_promotion_path_persists_decision(self):
        result = evaluate(_candidate(_passing_cases()), self.journal_path, promotion_path=self.promo_path)
        self.assertTrue(os.path.exists(self.promo_path))
        with open(self.promo_path, "r", encoding="utf-8") as fh:
            lines = [ln for ln in fh.read().splitlines() if ln.strip()]
        self.assertEqual(len(lines), 1)
        persisted = json.loads(lines[0])
        self.assertEqual(persisted["entry_id"], result["entry_id"])
        self.assertTrue(persisted["promoted"])

    def test_promotion_path_side_effect_free_on_journal(self):
        # Two decisions appended to the promotion file must not affect the journal
        # beyond the (idempotent) recorded entries. Use distinct candidates so
        # both are genuinely new journal entries.
        evaluate(_candidate(_passing_cases(), candidate_id="a"), self.journal_path, promotion_path=self.promo_path)
        evaluate(_candidate(_passing_cases(), candidate_id="b"), self.journal_path, promotion_path=self.promo_path)
        with open(self.promo_path, "r", encoding="utf-8") as fh:
            lines = [ln for ln in fh.read().splitlines() if ln.strip()]
        self.assertEqual(len(lines), 2)
        # Journal holds exactly the two recorded decisions; nothing mutated/removed.
        self.assertEqual(len(LearningJournal(self.journal_path).replay()), 2)

    def test_leaked_case_fails_closed(self):
        result = evaluate(_candidate(_leaked_cases()), self.journal_path)
        self.assertFalse(result["promoted"])
        self.assertFalse(result["holdout_passed"])
        self.assertEqual(result["holdout"]["leaked_cases"], 1)
        self.assertEqual(LearningJournal(self.journal_path).replay()[0]["action"], "reject")

    def test_reason_field_meaningful(self):
        ok = evaluate(_candidate(_passing_cases()), self.journal_path)
        self.assertEqual(ok["reason"], "holdout_passed")
        jr_fd, journal_r = tempfile.mkstemp(suffix=".jsonl")
        os.close(jr_fd)
        bad = evaluate(_candidate(_failing_cases()), journal_r)
        os.remove(journal_r)
        self.assertEqual(bad["reason"], "holdout_failed")

    def test_distinct_candidates_distinct_entries(self):
        evaluate(_candidate(_passing_cases(), candidate_id="a"), self.journal_path)
        evaluate(_candidate(_passing_cases(), candidate_id="b"), self.journal_path)
        entries = LearningJournal(self.journal_path).replay()
        self.assertEqual(len(entries), 2)
        self.assertNotEqual(entries[0]["entry_id"], entries[1]["entry_id"])


if __name__ == "__main__":
    unittest.main()

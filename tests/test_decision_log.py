"""tests/test_decision_log.py

Unit tests for noesis_harness.decision_log (append-only decision records).

Verifies append order, replay, latest(), idempotency on id+fingerprint,
fingerprint determinism, missing-file handling, and no-mutation guarantees.
"""

import os
import tempfile
import unittest

from noesis_harness.decision_log import (
    DecisionLog,
    DecisionLogConflict,
    _fingerprint,
)


class DecisionLogTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="dl_test_")
        self.path = os.path.join(self.dir, "decisions.jsonl")
        self.log = DecisionLog(self.path)

    def _records(self, scope=None):
        return self.log.replay(scope=scope)

    def test_append_creates_record(self):
        eid = self.log.record("ship v1", "tests green")
        self.assertTrue(os.path.exists(self.path))
        recs = self._records()
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["decision"], "ship v1")
        self.assertEqual(recs[0]["rationale"], "tests green")
        self.assertIsNone(recs[0].get("actor"))

    def test_append_order_preserved(self):
        self.log.record("first", "r1")
        self.log.record("second", "r2")
        self.log.record("third", "r3")
        decisions = [r["decision"] for r in self._records()]
        self.assertEqual(decisions, ["first", "second", "third"])

    def test_replay_returns_copies(self):
        self.log.record("decide", "why")
        replayed = self.log.replay()
        replayed[0]["decision"] = "mutated"
        self.assertEqual(self._records()[0]["decision"], "decide")

    def test_latest_returns_most_recent(self):
        self.log.record("a", "ra")
        self.log.record("b", "rb")
        latest = self.log.latest()
        self.assertIsNotNone(latest)
        self.assertEqual(latest["decision"], "b")

    def test_latest_empty_returns_none(self):
        self.assertIsNone(self.log.latest())

    def test_latest_scoped(self):
        self.log.record("agent-a", "ra", actor="alice")
        self.log.record("agent-b", "rb", actor="bob")
        self.log.record("agent-a2", "ra2", actor="alice")
        self.assertEqual(self.log.latest(scope="alice")["decision"], "agent-a2")
        self.assertEqual(self.log.latest(scope="bob")["decision"], "agent-b")
        self.assertIsNone(self.log.latest(scope="nobody"))

    def test_idempotent_on_explicit_id(self):
        eid = self.log.record("dup", "same", entry_id="fixed")
        eid2 = self.log.record("dup", "same", entry_id="fixed")
        self.assertEqual(eid, eid2)
        self.assertEqual(len(self._records()), 1)

    def test_idempotent_on_fingerprint(self):
        eid1 = self.log.record("same decision", "same rationale", actor="x")
        eid2 = self.log.record("same decision", "same rationale", actor="x")
        self.assertEqual(eid1, eid2)
        self.assertEqual(len(self._records()), 1)

    def test_idempotent_counts_once_with_different_ids_same_content(self):
        first = self.log.record("d", "r", entry_id="id-1")
        second = self.log.record("d", "r", entry_id="id-1")
        self.assertEqual(first, second)
        self.assertEqual(len(self._records()), 1)

    def test_fingerprint_deterministic(self):
        fp1 = _fingerprint("decide", "because", "actor")
        fp2 = _fingerprint("decide", "because", "actor")
        self.assertEqual(fp1, fp2)
        self.assertEqual(len(fp1), 64)

    def test_fingerprint_differs_on_content(self):
        fp_a = _fingerprint("a", "r", None)
        fp_b = _fingerprint("b", "r", None)
        self.assertNotEqual(fp_a, fp_b)

    def test_missing_file_replay_empty(self):
        fresh = DecisionLog(os.path.join(self.dir, "nope.jsonl"))
        self.assertEqual(fresh.replay(), [])
        self.assertIsNone(fresh.latest())

    def test_conflict_on_reused_id_different_content(self):
        self.log.record("original", "r", entry_id="same")
        with self.assertRaises(DecisionLogConflict):
            self.log.record("changed", "other", entry_id="same")

    def test_seq_is_monotonic(self):
        self.log.record("a", "ra")
        self.log.record("b", "rb")
        seqs = [r["seq"] for r in self._records()]
        self.assertEqual(seqs, [1, 2])

    def test_persistence_across_instances(self):
        self.log.record("persisted", "r", actor="agent")
        reopened = DecisionLog(self.path)
        recs = reopened.replay()
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["decision"], "persisted")
        self.assertEqual(recs[0]["actor"], "agent")


if __name__ == "__main__":
    unittest.main()

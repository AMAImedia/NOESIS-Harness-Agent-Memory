import json
import os
import tempfile
import threading
import time
import unittest

from noesis_harness.learning_journal import (
    LearningJournal,
    LearningJournalConflict,
)


class LearningJournalTests(unittest.TestCase):
    def journal(self):
        return LearningJournal(os.path.join(tempfile.mkdtemp(), "journal.jsonl"))

    def test_record_returns_deterministic_id_when_none(self):
        j = self.journal()
        ident = j.record("scope-a", "promote", {"k": "v"})
        self.assertTrue(ident)
        self.assertEqual(ident, j.record("scope-a", "promote", {"k": "v"}))

    def test_idempotent_append_same_entry_id_and_fingerprint(self):
        j = self.journal()
        ident = j.record("scope-a", "promote", {"x": 1}, entry_id="e1")
        self.assertEqual(ident, "e1")
        again = j.record("scope-a", "promote", {"x": 1}, entry_id="e1")
        self.assertEqual(again, "e1")
        self.assertEqual(len(j.replay()), 1)

    def test_conflict_raised_on_entry_id_reuse_with_different_content(self):
        j = self.journal()
        j.record("scope-a", "promote", {"x": 1}, entry_id="e1")
        with self.assertRaises(LearningJournalConflict):
            j.record("scope-a", "promote", {"x": 2}, entry_id="e1")

    def test_replay_is_ordered_and_pure(self):
        j = self.journal()
        j.record("s", "a", {"n": 1})
        j.record("s", "b", {"n": 2})
        j.record("s", "a", {"n": 3})
        entries = j.replay()
        self.assertEqual(len(entries), 3)
        actions = [e["action"] for e in entries]
        self.assertEqual(actions, ["a", "b", "a"])
        self.assertEqual(entries, j.replay())

    def test_replay_returns_dicts_with_required_fields(self):
        j = self.journal()
        j.record("scope-x", "record", {"detail": True})
        entry = j.replay()[0]
        for field in ("entry_id", "scope", "action", "payload", "ts", "fingerprint"):
            self.assertIn(field, entry)
        self.assertEqual(entry["scope"], "scope-x")
        self.assertEqual(entry["action"], "record")

    def test_fingerprint_is_sha256_of_content(self):
        import hashlib
        j = self.journal()
        j.record("s", "a", {"k": "v"}, entry_id="e1")
        entry = j.replay()[0]
        canon = json.dumps(
            {"scope": "s", "action": "a", "payload": {"k": "v"}},
            ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        )
        expected = hashlib.sha256(canon.encode("utf-8")).hexdigest()
        self.assertEqual(entry["fingerprint"], expected)

    def test_fingerprint_uniqueness_across_distinct_payloads(self):
        j = self.journal()
        ids = {
            j.record("s", "a", {"n": i}, entry_id="e%d" % i) for i in range(20)
        }
        self.assertEqual(len(ids), 20)
        fingerprints = {e["fingerprint"] for e in j.replay()}
        self.assertEqual(len(fingerprints), 20)

    def test_holdout_summary_counts_and_bounds(self):
        j = self.journal()
        j.record("s", "promote", {"n": 1}, entry_id="a")
        j.record("s", "reject", {"n": 2}, entry_id="b")
        j.record("s", "promote", {"n": 3}, entry_id="c")
        summary = j.holdout_summary()
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["counts"], {"promote": 2, "reject": 1})
        self.assertGreaterEqual(summary["latest_ts"], summary["earliest_ts"])
        self.assertTrue(summary["replay_digest"])

    def test_holdout_summary_stability_across_replays(self):
        j = self.journal()
        for i in range(10):
            j.record("s", "a" if i % 2 else "b", {"i": i}, entry_id="e%d" % i)
        first = j.holdout_summary()
        second = j.holdout_summary()
        self.assertEqual(first, second)

    def test_holdout_summary_empty(self):
        j = self.journal()
        summary = j.holdout_summary()
        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["counts"], {})
        self.assertEqual(summary["earliest_ts"], 0.0)
        self.assertEqual(summary["latest_ts"], 0.0)
        self.assertTrue(summary["replay_digest"])

    def test_persistence_across_reopen(self):
        path = os.path.join(tempfile.mkdtemp(), "journal.jsonl")
        j1 = LearningJournal(path)
        j1.record("s", "a", {"v": 1}, entry_id="e1")
        j2 = LearningJournal(path)
        self.assertEqual(len(j2.replay()), 1)
        self.assertEqual(j2.replay()[0]["entry_id"], "e1")

    def test_concurrency_safe_append(self):
        j = self.journal()
        barrier = threading.Barrier(8)
        errors = []

        def worker(idx):
            try:
                barrier.wait()
                for k in range(50):
                    j.record("scope", "act", {"w": idx, "k": k}, entry_id="w%d-k%d" % (idx, k))
            except Exception as exc:  # pragma: no cover - defensive
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(j.replay()), 8 * 50)

    def test_concurrent_idempotent_appends_collapse(self):
        j = self.journal()
        barrier = threading.Barrier(6)

        def worker():
            barrier.wait()
            j.record("s", "a", {"shared": True}, entry_id="shared")

        threads = [threading.Thread(target=worker) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(j.replay()), 1)

    def test_invalid_scope_and_action_rejected(self):
        j = self.journal()
        with self.assertRaises(ValueError):
            j.record("", "a", {})
        with self.assertRaises(ValueError):
            j.record("s", "", {})

    def test_non_serializable_payload_rejected(self):
        j = self.journal()
        with self.assertRaises(ValueError):
            j.record("s", "a", {"bad": object()})


if __name__ == "__main__":
    unittest.main()

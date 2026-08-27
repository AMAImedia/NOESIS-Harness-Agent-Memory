"""tests/test_quota_tracker.py

Unit tests for noesis_harness.quota_tracker.QuotaTracker.
"""

from __future__ import annotations

import os
import tempfile
import unittest

from noesis_harness.quota_tracker import QuotaTracker


class QuotaTrackerTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "quota.jsonl")

    def test_record_and_used(self):
        qt = QuotaTracker(self.path)
        qt.record("api", 3)
        qt.record("api", 7)
        self.assertEqual(qt.used("api"), 10)

    def test_remaining_under_limit(self):
        qt = QuotaTracker(self.path)
        qt.record("api", 4)
        self.assertEqual(qt.remaining("api", 10), 6)

    def test_remaining_over_limit_clamped(self):
        qt = QuotaTracker(self.path)
        qt.record("api", 15)
        self.assertEqual(qt.remaining("api", 10), 0)

    def test_remaining_exact_limit(self):
        qt = QuotaTracker(self.path)
        qt.record("api", 10)
        self.assertEqual(qt.remaining("api", 10), 0)

    def test_idempotent_on_entry_id(self):
        qt = QuotaTracker(self.path)
        first = qt.record("api", 5, entry_id="e1")
        second = qt.record("api", 5, entry_id="e1")
        self.assertTrue(first["recorded"])
        self.assertFalse(second["recorded"])
        self.assertEqual(qt.used("api"), 5)

    def test_idempotent_on_fingerprint_without_entry_id(self):
        qt = QuotaTracker(self.path)
        first = qt.record("api", 5)
        second = qt.record("api", 5)
        self.assertTrue(first["recorded"])
        self.assertFalse(second["recorded"])
        self.assertEqual(qt.used("api"), 5)

    def test_fingerprint_determinism(self):
        qt = QuotaTracker(self.path)
        fp1 = QuotaTracker._fingerprint("api", 5, "e1")
        fp2 = QuotaTracker._fingerprint("api", 5, "e1")
        fp3 = QuotaTracker._fingerprint("api", 6, "e1")
        self.assertEqual(fp1, fp2)
        self.assertNotEqual(fp1, fp3)

    def test_replay_from_disk(self):
        qt = QuotaTracker(self.path)
        qt.record("api", 2, entry_id="a")
        qt.record("db", 3, entry_id="b")
        qt2 = QuotaTracker(self.path)
        self.assertEqual(qt2.used("api"), 2)
        self.assertEqual(qt2.used("db"), 3)

    def test_missing_file_treated_as_empty(self):
        fresh = os.path.join(self.dir, "nope", "missing.jsonl")
        qt = QuotaTracker(fresh)
        self.assertEqual(qt.used("api"), 0)
        self.assertTrue(os.path.exists(fresh))

    def test_no_mutation_of_existing_entries(self):
        qt = QuotaTracker(self.path)
        qt.record("api", 4, entry_id="x")
        before = qt.used("api")
        # re-recording the same event must not change usage
        qt.record("api", 4, entry_id="x")
        after = qt.used("api")
        self.assertEqual(before, after)
        # a genuinely new event does not alter prior ones
        qt.record("api", 1, entry_id="y")
        self.assertEqual(qt.used("api"), 5)
        # count lines in file == distinct events only
        with open(self.path, "r", encoding="utf-8") as fh:
            lines = [l for l in fh if l.strip()]
        self.assertEqual(len(lines), 2)

    def test_multi_scope_isolation(self):
        qt = QuotaTracker(self.path)
        qt.record("api", 5)
        qt.record("db", 8)
        qt.record("api", 2)
        self.assertEqual(qt.used("api"), 7)
        self.assertEqual(qt.used("db"), 8)
        self.assertEqual(qt.remaining("api", 10), 3)
        self.assertEqual(qt.remaining("db", 10), 2)
        self.assertEqual(qt.scopes(), ["api", "db"])

    def test_different_entry_id_same_content_distinct(self):
        qt = QuotaTracker(self.path)
        qt.record("api", 5, entry_id="e1")
        qt.record("api", 5, entry_id="e2")
        self.assertEqual(qt.used("api"), 10)


if __name__ == "__main__":
    unittest.main()

"""Tests for noesis_harness.consent_log.

Stdlib-only. Validates append-only semantics, latest-wins resolution, fingerprint
determinism, idempotency, missing-file handling, and read-only safety.
"""

import os
import tempfile
import unittest

from noesis_harness.consent_log import ConsentLog, _fingerprint


class TestConsentLog(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="consent_test_")
        self.path = os.path.join(self.tmp, "consent.jsonl")

    def _log(self):
        return ConsentLog(self.path)

    def test_record_and_replay(self):
        log = self._log()
        log.record("alice", "read:docs", True, evidence="form")
        log.record("bob", "read:docs", False)
        records = log.replay()
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["subject"], "alice")
        self.assertTrue(records[0]["granted"])
        self.assertEqual(records[1]["subject"], "bob")
        self.assertFalse(records[1]["granted"])

    def test_latest_wins_per_scope(self):
        log = self._log()
        log.record("alice", "export", False, evidence="e1")
        log.record("alice", "export", True, evidence="e2")
        self.assertTrue(log.granted_for("export"))
        log.record("alice", "export", False, evidence="e3")
        self.assertFalse(log.granted_for("export"))

    def test_granted_for_unknown_scope_fail_closed(self):
        log = self._log()
        self.assertFalse(log.granted_for("never:seen"))

    def test_fingerprint_determinism(self):
        fp1 = _fingerprint("subj", "scope", True, {"k": "v"})
        fp2 = _fingerprint("subj", "scope", True, {"k": "v"})
        self.assertEqual(fp1, fp2)
        # Different evidence must change the fingerprint.
        fp3 = _fingerprint("subj", "scope", True, {"k": "other"})
        self.assertNotEqual(fp1, fp3)
        # Different granted must change the fingerprint.
        fp4 = _fingerprint("subj", "scope", False, {"k": "v"})
        self.assertNotEqual(fp1, fp4)

    def test_idempotent_by_fingerprint(self):
        log = self._log()
        eid = log.record("alice", "scope", True, evidence="x")
        eid2 = log.record("alice", "scope", True, evidence="x")
        self.assertEqual(eid, eid2)
        self.assertEqual(len(log.replay()), 1)

    def test_idempotent_by_entry_id(self):
        log = self._log()
        log.record("alice", "scope", True, evidence="x", entry_id="fixed-1")
        log.record("alice", "scope", True, evidence="x", entry_id="fixed-1")
        self.assertEqual(len(log.replay()), 1)

    def test_entry_id_reuse_with_different_content_raises(self):
        log = self._log()
        log.record("alice", "scope", True, evidence="x", entry_id="fixed-1")
        with self.assertRaises(ValueError):
            log.record("alice", "scope", False, evidence="x", entry_id="fixed-1")

    def test_missing_file_returns_empty_replay(self):
        self.assertFalse(os.path.exists(self.path))
        log = self._log()
        self.assertEqual(log.replay(), [])
        self.assertFalse(log.granted_for("anything"))

    def test_replay_is_read_only(self):
        log = self._log()
        log.record("alice", "scope", True, evidence="x")
        records = log.replay()
        records.append({"injected": True})
        # The file must be untouched; a fresh replay must not see the injection.
        fresh = self._log()
        self.assertEqual(len(fresh.replay()), 1)

    def test_replay_across_instances(self):
        log1 = self._log()
        log1.record("alice", "scope", True)
        log2 = ConsentLog(self.path)
        self.assertEqual(len(log2.replay()), 1)
        self.assertTrue(log2.granted_for("scope"))

    def test_scope_isolation(self):
        log = self._log()
        log.record("alice", "read", True)
        log.record("alice", "write", False)
        self.assertTrue(log.granted_for("read"))
        self.assertFalse(log.granted_for("write"))

    def test_append_only_no_mutation_of_existing(self):
        log = self._log()
        log.record("alice", "scope", True, evidence="a")
        # Append a second, conflicting decision; the first record must remain.
        log.record("alice", "scope", False, evidence="b")
        records = log.replay()
        self.assertEqual(len(records), 2)
        self.assertTrue(records[0]["granted"])
        self.assertEqual(records[0]["evidence"], "a")


if __name__ == "__main__":
    unittest.main()

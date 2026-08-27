"""Tests for noesis_harness/approval_log.py

Covers the request/approve/deny lifecycle, state resolution, unknown ids,
replay, idempotency, missing-file handling, and log immutability.
"""

import os
import tempfile
import unittest

from noesis_harness.approval_log import (
    ApprovalLog,
    STATE_APPROVED,
    STATE_DENIED,
    STATE_PENDING,
)


class ApprovalLogTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="approval_log_test_")
        self.path = os.path.join(self.dir, "approval.jsonl")

    def _new(self):
        return ApprovalLog(self.path)

    def test_request_returns_id_and_starts_pending(self):
        log = self._new()
        rid = log.request("deploy", "alice")
        self.assertTrue(rid)
        self.assertEqual(log.state(rid), STATE_PENDING)

    def test_full_lifecycle_approve(self):
        log = self._new()
        rid = log.request("delete_bucket", "alice")
        self.assertEqual(log.state(rid), STATE_PENDING)
        log.approve(rid, "bob")
        self.assertEqual(log.state(rid), STATE_APPROVED)

    def test_full_lifecycle_deny_with_reason(self):
        log = self._new()
        rid = log.request("wipe_data", "alice")
        log.deny(rid, "bob", "too risky")
        self.assertEqual(log.state(rid), STATE_DENIED)

    def test_deny_reason_recorded(self):
        log = self._new()
        rid = log.request("x", "alice")
        log.deny(rid, "bob", "policy violation")
        recs = [r for r in log.replay() if r.get("event") == "deny"]
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["reason"], "policy violation")
        self.assertEqual(recs[0]["approver"], "bob")

    def test_state_unknown_id_is_none(self):
        log = self._new()
        self.assertIsNone(log.state("does-not-exist"))

    def test_approve_unknown_id_raises(self):
        log = self._new()
        with self.assertRaises(ValueError):
            log.approve("nope", "bob")

    def test_deny_unknown_id_raises(self):
        log = self._new()
        with self.assertRaises(ValueError):
            log.deny("nope", "bob", "x")

    def test_replay_preserves_append_order(self):
        log = self._new()
        r1 = log.request("a", "alice")
        r2 = log.request("b", "carol")
        log.approve(r1, "bob")
        events = log.replay()
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0]["event"], "request")
        self.assertEqual(events[0]["request_id"], r1)
        self.assertEqual(events[2]["event"], "approve")
        self.assertEqual(events[2]["request_id"], r1)
        self.assertEqual(events[1]["request_id"], r2)

    def test_replay_returns_copies_not_live_refs(self):
        log = self._new()
        rid = log.request("a", "alice")
        snapshot = log.replay()
        snapshot[0]["request_id"] = "mutated"
        self.assertEqual(log.state(rid), STATE_PENDING)

    def test_request_idempotent_on_entry_id(self):
        log = self._new()
        rid = log.request("a", "alice", entry_id="fixed-1")
        rid2 = log.request("a", "alice", entry_id="fixed-1")
        self.assertEqual(rid, rid2)
        requests = [r for r in log.replay() if r.get("event") == "request"]
        self.assertEqual(len(requests), 1)

    def test_request_entry_id_conflict_raises(self):
        log = self._new()
        log.request("a", "alice", entry_id="fixed-1")
        with self.assertRaises(ValueError):
            log.request("b", "alice", entry_id="fixed-1")

    def test_approve_idempotent_double_send(self):
        log = self._new()
        rid = log.request("a", "alice")
        log.approve(rid, "bob")
        log.approve(rid, "bob")
        approves = [r for r in log.replay() if r.get("event") == "approve"]
        self.assertEqual(len(approves), 1)
        self.assertEqual(log.state(rid), STATE_APPROVED)

    def test_deny_idempotent_double_send(self):
        log = self._new()
        rid = log.request("a", "alice")
        log.deny(rid, "bob", "reason")
        log.deny(rid, "bob", "reason")
        denies = [r for r in log.replay() if r.get("event") == "deny"]
        self.assertEqual(len(denies), 1)
        self.assertEqual(log.state(rid), STATE_DENIED)

    def test_conflicting_decision_raises(self):
        log = self._new()
        rid = log.request("a", "alice")
        log.approve(rid, "bob")
        with self.assertRaises(ValueError):
            log.deny(rid, "carol", "override")

    def test_missing_file_opens_empty(self):
        log = self._new()
        self.assertEqual(log.replay(), [])
        self.assertIsNone(log.state("anything"))

    def test_persists_across_reopen(self):
        log = self._new()
        rid = log.request("a", "alice")
        log.deny(rid, "bob", "nope")
        reopened = ApprovalLog(self.path)
        self.assertEqual(reopened.state(rid), STATE_DENIED)
        self.assertEqual(len(reopened.replay()), 2)

    def test_log_is_append_only_not_mutated(self):
        log = self._new()
        rid = log.request("a", "alice")
        log.approve(rid, "bob")
        before = log.replay()
        # deriving state must not change the file
        log.state(rid)
        log.replay()
        after = self._new().replay()
        self.assertEqual(before, after)
        self.assertEqual(len(after), 2)


if __name__ == "__main__":
    unittest.main()

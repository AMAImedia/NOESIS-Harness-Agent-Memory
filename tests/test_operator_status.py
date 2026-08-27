"""Tests for noesis_harness.operator_status (Track A operator surface).

Read-only health snapshot: it never mutates the event log or lease store.
These tests build a temp event log via EventStore and a temp lease db via
coordination.Leases, then assert on the status dict shape, the deterministic
expired/active split, digest stability, JSON output, and CLI exit code.
"""

import json
import os
import sqlite3
import tempfile
import unittest

from noesis_harness import operator_status
from noesis_harness.coordination import Leases
from noesis_harness.event_store import EventStore
from noesis_harness.self_audit import run_self_audit


def _build_event_log(path):
    store = EventStore(path)
    store.append("note", {"x": 1}, event_id="a")
    store.append("note", {"x": 2}, event_id="b")
    store.append("note", {"x": 3}, event_id="c")
    return store


class TestCollectStatus(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.events = os.path.join(self.tmp, "events.jsonl")
        self.leases_db = os.path.join(self.tmp, "leases.db")

    def test_missing_stores(self):
        status = operator_status.collect_status()
        self.assertFalse(status["event_log"]["present"])
        self.assertFalse(status["leases"]["present"])
        self.assertIsNone(status["self_audit"])
        self.assertTrue(status["ok"])

    def test_event_log_stats(self):
        _build_event_log(self.events)
        status = operator_status.collect_status(events_path=self.events)
        el = status["event_log"]
        self.assertTrue(el["present"])
        self.assertEqual(el["record_count"], 3)
        self.assertEqual(el["last_seq"], 3)
        self.assertEqual(el["last_event_id"], "c")

    def test_lease_stats_active_only(self):
        leases = Leases(self.leases_db, ttl=10 * 60)
        # All acquired "now"; with now=max(acquired_at) none are expired.
        leases.acquire("task1", "agent_a")
        leases.acquire("task2", "agent_b")
        status = operator_status.collect_status(leases_path=self.leases_db)
        ls = status["leases"]
        self.assertTrue(ls["present"])
        self.assertTrue(ls["table_present"])
        self.assertEqual(ls["active_count"], 2)
        self.assertEqual(ls["expired_count"], 0)

    def test_lease_stats_with_expired(self):
        leases = Leases(self.leases_db, ttl=10 * 60)
        leases.acquire("task1", "agent_a")
        # Hand-write an already-expired active lease (expires_at in the past
        # relative to the max acquired_at of the other rows).
        with sqlite3.connect(self.leases_db) as c:
            import time
            base = time.time()
            c.execute(
                "INSERT OR REPLACE INTO leases "
                "(task_key, holder, acquired_at, expires_at, status) VALUES (?,?,?,?,?)",
                ("stale", "agent_z", base - 1000, base - 500, "active"))
        status = operator_status.collect_status(leases_path=self.leases_db)
        ls = status["leases"]
        # now = max(acquired_at) = base (task1), so 'stale' is expired.
        self.assertEqual(ls["active_count"], 2)
        self.assertEqual(ls["expired_count"], 1)

    def test_released_leases_not_counted(self):
        leases = Leases(self.leases_db, ttl=10 * 60)
        leases.acquire("task1", "agent_a")
        leases.acquire("task2", "agent_b")
        leases.release("task2", "agent_b")
        status = operator_status.collect_status(leases_path=self.leases_db)
        ls = status["leases"]
        self.assertEqual(ls["active_count"], 1)
        self.assertEqual(ls["expired_count"], 0)

    def test_digest_present_when_paths_given(self):
        _build_event_log(self.events)
        leases = Leases(self.leases_db, ttl=10 * 60)
        leases.acquire("task1", "agent_a")
        status = operator_status.collect_status(self.events, self.leases_db)
        self.assertIsNotNone(status["self_audit"])
        expected = run_self_audit(self.events, self.leases_db).digest()
        self.assertEqual(status["self_audit"], expected)

    def test_digest_stability(self):
        _build_event_log(self.events)
        leases = Leases(self.leases_db, ttl=10 * 60)
        leases.acquire("task1", "agent_a")
        s1 = operator_status.collect_status(self.events, self.leases_db)
        s2 = operator_status.collect_status(self.events, self.leases_db)
        self.assertEqual(s1["self_audit"], s2["self_audit"])

    def test_ok_true_for_clean_stores(self):
        _build_event_log(self.events)
        leases = Leases(self.leases_db, ttl=10 * 60)
        leases.acquire("task1", "agent_a")
        status = operator_status.collect_status(self.events, self.leases_db)
        self.assertTrue(status["ok"])


class TestOperatorStatusCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.events = os.path.join(self.tmp, "events.jsonl")
        self.leases_db = os.path.join(self.tmp, "leases.db")

    def test_exit_code_zero(self):
        _build_event_log(self.events)
        leases = Leases(self.leases_db, ttl=10 * 60)
        leases.acquire("task1", "agent_a")
        rc = operator_status.main([
            "--events", self.events, "--leases", self.leases_db])
        self.assertEqual(rc, 0)

    def test_json_output_shape(self):
        _build_event_log(self.events)
        leases = Leases(self.leases_db, ttl=10 * 60)
        leases.acquire("task1", "agent_a")
        import io
        import sys
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            rc = operator_status.main([
                "--events", self.events, "--leases", self.leases_db, "--json"])
        finally:
            sys.stdout = old
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertIn("event_log", payload)
        self.assertIn("leases", payload)
        self.assertIn("self_audit", payload)
        self.assertIn("ok", payload)
        self.assertEqual(payload["event_log"]["record_count"], 3)

    def test_human_output_runs(self):
        _build_event_log(self.events)
        import io
        import sys
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            rc = operator_status.main(["--events", self.events])
        finally:
            sys.stdout = old
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("NOESIS operator status", out)
        self.assertIn("records:", out)

    def test_no_stores_no_error(self):
        rc = operator_status.main([])
        self.assertEqual(rc, 0)

    def test_read_only_no_mutation(self):
        _build_event_log(self.events)
        before = os.path.getsize(self.events)
        operator_status.collect_status(self.events, self.leases_db)
        after = os.path.getsize(self.events)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

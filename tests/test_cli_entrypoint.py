"""Tests for noesis_harness.__main__ (Track A operator front-door).

The CLI is a thin, read-only dispatcher over operator_status, self_audit, and
recall_augment. These tests drive every subcommand against a temp event log
(EventStore) and a temp lease db (coordination.Leases), assert that --json
output parses, that exit codes are correct, and that an unknown subcommand is
handled without mutating any state.
"""

import io
import json
import os
import sys
import tempfile
import unittest

from noesis_harness import recall_augment
from noesis_harness.__main__ import main
from noesis_harness.coordination import Leases
from noesis_harness.event_store import EventStore


def _build_event_log(path):
    store = EventStore(path)
    store.append("note", {"topic": "alpha"}, event_id="a")
    store.append("note", {"topic": "beta"}, event_id="b")
    store.append("note", {"topic": "alpha again"}, event_id="c")
    return store


def _build_lease_db(path):
    leases = Leases(path, ttl=10 * 60)
    leases.acquire("task1", "agent_a")
    leases.acquire("task2", "agent_b")
    return leases


def _capture(func, *call_args):
    """Run `func(*call_args)`, capture stdout, return (rc, out)."""
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        rc = func(*call_args)
    finally:
        sys.stdout = old
    return rc, buf.getvalue()


class TestStatusSubcommand(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.events = os.path.join(self.tmp, "events.jsonl")
        self.leases_db = os.path.join(self.tmp, "leases.db")

    def test_status_exit_zero(self):
        _build_event_log(self.events)
        _build_lease_db(self.leases_db)
        rc, _ = _capture(main,
            ["status", "--events", self.events, "--leases", self.leases_db])
        self.assertEqual(rc, 0)

    def test_status_json_parses(self):
        _build_event_log(self.events)
        _build_lease_db(self.leases_db)
        rc, out = _capture(main,
            ["status", "--events", self.events, "--leases", self.leases_db, "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertIn("event_log", payload)
        self.assertIn("leases", payload)
        self.assertEqual(payload["event_log"]["record_count"], 3)

    def test_status_read_only(self):
        _build_event_log(self.events)
        before = os.path.getsize(self.events)
        _capture(main,
                 ["status", "--events", self.events])
        self.assertEqual(os.path.getsize(self.events), before)


class TestAuditSubcommand(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.events = os.path.join(self.tmp, "events.jsonl")
        self.leases_db = os.path.join(self.tmp, "leases.db")

    def test_audit_exit_zero_clean(self):
        _build_event_log(self.events)
        rc, _ = _capture(main,
            ["audit", "--events", self.events])
        self.assertEqual(rc, 0)

    def test_audit_json_parses(self):
        _build_event_log(self.events)
        rc, out = _capture(main,
            ["audit", "--events", self.events, "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertIn("scope", payload)
        self.assertIn("ok", payload)
        self.assertIn("digest", payload)

    def test_audit_now_flag_accepted(self):
        _build_event_log(self.events)
        _build_lease_db(self.leases_db)
        rc, _ = _capture(main,
            ["audit", "--events", self.events, "--leases", self.leases_db,
             "--now", "1.0"])
        self.assertEqual(rc, 0)

    def test_audit_strict_nonzero_on_failure(self):
        # Non-monotonic sequence numbers => error finding => strict fails.
        with open(self.events, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(
                {"event_id": "a", "type": "note", "payload": {"x": 1}, "seq": 2}) + "\n")
            fh.write(json.dumps(
                {"event_id": "b", "type": "note", "payload": {"x": 2}, "seq": 1}) + "\n")
        rc, _ = _capture(main,
            ["audit", "--events", self.events, "--strict"])
        self.assertEqual(rc, 1)


class TestRecallSubcommand(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.events = os.path.join(self.tmp, "events.jsonl")

    def test_recall_prints_context_exit_zero(self):
        _build_event_log(self.events)
        rc, out = _capture(main,
            ["recall", "--query", "alpha", "--events", self.events])
        self.assertEqual(rc, 0)
        self.assertIn("Recalled context", out)

    def test_recall_matches_module_output(self):
        _build_event_log(self.events)
        rc, out = _capture(main,
            ["recall", "--query", "alpha", "--events", self.events, "--top-k", "1"])
        expected = recall_augment.build_augmented_context("alpha", self.events, 1)
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), expected.strip())

    def test_recall_top_k_limits(self):
        _build_event_log(self.events)
        rc, out = _capture(main,
            ["recall", "--query", "alpha", "--events", self.events, "--top-k", "0"])
        self.assertEqual(rc, 0)
        # top_k=0 yields no ranked events -> empty context -> no output.
        self.assertEqual(out.strip(), "")

    def test_recall_no_match_exit_zero(self):
        _build_event_log(self.events)
        rc, out = _capture(main,
            ["recall", "--query", "zzz-nonexistent", "--events", self.events])
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), "")


class TestDispatchErrors(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.events = os.path.join(self.tmp, "events.jsonl")

    def test_unknown_subcommand_handled(self):
        rc, _ = _capture(main, ["bogus"])
        self.assertNotEqual(rc, 0)

    def test_no_subcommand_handled(self):
        rc, _ = _capture(main, [])
        self.assertNotEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()

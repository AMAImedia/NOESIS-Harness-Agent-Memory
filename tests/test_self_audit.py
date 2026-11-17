"""Tests for noesis_harness.self_audit (Track A control-plane self-audit).

Read-only, append-only-safe auditor: it never writes to the event log or the
lease store. These tests exercise every finding path, determinism of the
digest, and the CLI entry point.
"""

import json
import os
import sqlite3
import tempfile
import unittest

from noesis_harness import self_audit
from noesis_harness.self_audit import (
    AuditReport,
    audit_coordination,
    audit_event_store,
    main,
    run_self_audit,
)


def _write_events(path, records):
    with open(path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _fp(event_type, payload):
    return self_audit._fingerprint(event_type, payload)


class TestEventStoreAuditClean(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "events.jsonl")

    def test_clean_log_is_ok(self):
        _write_events(self.path, [
            {"event_id": "a", "type": "note", "payload": {"x": 1}, "seq": 1},
            {"event_id": "b", "type": "note", "payload": {"x": 2}, "seq": 2},
            {"event_id": "c", "type": "note", "payload": {"x": 3}, "seq": 3},
        ])
        rep = audit_event_store(self.path)
        self.assertTrue(rep.ok)
        self.assertEqual(rep.findings, [])

    def test_missing_file_is_info_not_error(self):
        rep = audit_event_store(os.path.join(self.tmp, "nope.jsonl"))
        self.assertTrue(rep.ok)
        self.assertEqual(rep.findings[0]["code"], self_audit.CODE_SCOPE_MISSING)

    def test_deterministic_digest(self):
        _write_events(self.path, [
            {"event_id": "a", "type": "note", "payload": {"x": 1}, "seq": 1},
            {"event_id": "b", "type": "note", "payload": {"x": 2}, "seq": 2},
        ])
        self.assertEqual(audit_event_store(self.path).digest(),
                         audit_event_store(self.path).digest())


class TestEventStoreAuditFindings(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "events.jsonl")

    def test_event_id_conflict_is_error(self):
        _write_events(self.path, [
            {"event_id": "a", "type": "note", "payload": {"x": 1}, "seq": 1},
            {"event_id": "a", "type": "note", "payload": {"x": 999}, "seq": 2},
        ])
        rep = audit_event_store(self.path)
        self.assertFalse(rep.ok)
        codes = [f["code"] for f in rep.findings]
        self.assertIn(self_audit.CODE_EVENT_ID_CONFLICT, codes)

    def test_idempotent_duplicate_is_info(self):
        rec = {"event_id": "a", "type": "note", "payload": {"x": 1}, "seq": 1}
        rec2 = {"event_id": "a", "type": "note", "payload": {"x": 1}, "seq": 2}
        _write_events(self.path, [rec, rec2])
        rep = audit_event_store(self.path)
        self.assertTrue(rep.ok)
        self.assertTrue(any(f["code"] == self_audit.CODE_IDEMPOTENT_DUPLICATE
                            for f in rep.findings))

    def test_content_duplicate_under_two_ids_is_warn(self):
        payload = {"x": 1}
        _write_events(self.path, [
            {"event_id": "a", "type": "note", "payload": payload, "seq": 1},
            {"event_id": "b", "type": "note", "payload": dict(payload), "seq": 2},
        ])
        rep = audit_event_store(self.path)
        self.assertTrue(rep.ok)  # warn is advisory, not a hard failure
        self.assertTrue(any(f["code"] == self_audit.CODE_CONTENT_DUPLICATE
                            for f in rep.findings))

    def test_non_monotonic_seq_is_error(self):
        _write_events(self.path, [
            {"event_id": "a", "type": "note", "payload": {"x": 1}, "seq": 2},
            {"event_id": "b", "type": "note", "payload": {"x": 2}, "seq": 1},
        ])
        rep = audit_event_store(self.path)
        self.assertFalse(rep.ok)
        self.assertTrue(any(f["code"] == self_audit.CODE_SEQ_NOT_MONOTONIC
                            for f in rep.findings))

    def test_seq_gap_is_warn(self):
        _write_events(self.path, [
            {"event_id": "a", "type": "note", "payload": {"x": 1}, "seq": 1},
            {"event_id": "b", "type": "note", "payload": {"x": 2}, "seq": 5},
        ])
        rep = audit_event_store(self.path)
        self.assertTrue(rep.ok)  # warn is advisory
        self.assertTrue(any(f["code"] == self_audit.CODE_SEQ_GAP
                            for f in rep.findings))

    def test_tail_corruption_is_info(self):
        _write_events(self.path, [
            {"event_id": "a", "type": "note", "payload": {"x": 1}, "seq": 1},
        ])
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write("{ this is not json\n")
        rep = audit_event_store(self.path)
        self.assertTrue(rep.ok)
        self.assertTrue(any(f["code"] == self_audit.CODE_LOG_TAIL_CORRUPTION
                            for f in rep.findings))

    def test_non_tail_corruption_is_critical(self):
        _write_events(self.path, [
            {"event_id": "a", "type": "note", "payload": {"x": 1}, "seq": 1},
        ])
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write("{ broken middle\n")
            fh.write(json.dumps({"event_id": "b", "type": "note",
                                  "payload": {"x": 2}, "seq": 2}) + "\n")
        rep = audit_event_store(self.path)
        self.assertFalse(rep.ok)
        self.assertTrue(any(f["code"] == self_audit.CODE_LOG_CORRUPT_NON_TAIL
                            for f in rep.findings))

    def test_non_object_record_is_error(self):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write("[1, 2, 3]\n")
        rep = audit_event_store(self.path)
        self.assertFalse(rep.ok)
        self.assertTrue(any(f["code"] == self_audit.CODE_LOG_NOT_OBJECT
                            for f in rep.findings))


class TestCoordinationAudit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "coord.sqlite3")

    def _seed(self, rows):
        conn = sqlite3.connect(self.db, timeout=10)
        conn.execute("CREATE TABLE leases ("
                     " task_key TEXT PRIMARY KEY,"
                     " holder TEXT NOT NULL,"
                     " acquired_at REAL NOT NULL,"
                     " expires_at REAL NOT NULL,"
                     " status TEXT NOT NULL DEFAULT 'active')")
        conn.executemany(
            "INSERT INTO leases VALUES (?,?,?,?,?)", rows)
        conn.commit()
        conn.close()

    def test_missing_db_is_info(self):
        rep = audit_coordination(os.path.join(self.tmp, "nope.sqlite3"))
        self.assertTrue(rep.ok)
        self.assertEqual(rep.findings[0]["code"], self_audit.CODE_SCOPE_MISSING)

    def test_missing_table_is_info(self):
        conn = sqlite3.connect(self.db, timeout=10)
        conn.execute("CREATE TABLE other (id INTEGER)")
        conn.commit()
        conn.close()
        rep = audit_coordination(self.db)
        self.assertTrue(rep.ok)
        self.assertTrue(any(f["code"] == self_audit.CODE_LEASE_TABLE_MISSING
                            for f in rep.findings))

    def test_expired_active_lease_is_warn(self):
        now = 1000.0
        self._seed([
            ("t1", "agent1", now - 100, now - 10, "active"),
            ("t2", "agent2", now - 100, now + 100, "active"),
        ])
        rep = audit_coordination(self.db, now=now)
        self.assertTrue(rep.ok)  # warn is advisory
        self.assertTrue(any(f["code"] == self_audit.CODE_LEASE_EXPIRED_ACTIVE
                            for f in rep.findings))

    def test_holder_overlap_is_warn(self):
        now = 1000.0
        self._seed([
            ("t1", "agent1", now - 100, now + 100, "active"),
            ("t2", "agent1", now - 100, now + 100, "active"),
        ])
        rep = audit_coordination(self.db, now=now)
        self.assertTrue(rep.ok)  # warn is advisory
        self.assertTrue(any(f["code"] == self_audit.CODE_LEASE_HOLDER_OVERLAP
                            for f in rep.findings))

    def test_clean_leases_are_ok(self):
        now = 1000.0
        self._seed([
            ("t1", "agent1", now - 100, now + 100, "active"),
            ("t2", "agent2", now - 100, now + 100, "active"),
        ])
        rep = audit_coordination(self.db, now=now)
        self.assertTrue(rep.ok)

    def test_default_now_is_deterministic_from_data(self):
        self._seed([
            ("t1", "agent1", 500.0, 1000.0, "active"),
        ])
        self.assertEqual(audit_coordination(self.db).digest(),
                         audit_coordination(self.db).digest())


class TestCombinedAudit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.events = os.path.join(self.tmp, "events.jsonl")
        self.db = os.path.join(self.tmp, "coord.sqlite3")

    def test_combined_merges_scopes(self):
        _write_events(self.events, [
            {"event_id": "a", "type": "note", "payload": {"x": 1}, "seq": 1},
        ])
        rep = run_self_audit(events_path=self.events)
        self.assertTrue(rep.ok)
        self.assertEqual(rep.scope, "control_plane")
        for f in rep.findings:
            self.assertIn("scope", f)

    def test_cli_json_output_and_strict(self):
        _write_events(self.events, [
            {"event_id": "a", "type": "note", "payload": {"x": 1}, "seq": 2},
            {"event_id": "b", "type": "note", "payload": {"x": 2}, "seq": 1},
        ])
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(["--events", self.events, "--json", "--strict"])
        self.assertEqual(rc, 1)
        payload = json.loads(buf.getvalue())
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["digest"], run_self_audit(
            events_path=self.events).digest())

    def test_cli_default_non_strict_returns_zero(self):
        _write_events(self.events, [
            {"event_id": "a", "type": "note", "payload": {"x": 1}, "seq": 1},
        ])
        self.assertEqual(main(["--events", self.events]), 0)


if __name__ == "__main__":
    unittest.main()

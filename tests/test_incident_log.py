"""Tests for noesis_harness/incident_log.py

Stdlib-only. Exercises the open/close lifecycle, status transitions, unknown-id
behaviour, replay projection, idempotent append, missing-file handling, and the
no-mutation guarantee of status()/replay().
"""

import os
import tempfile
import unittest

from noesis_harness.incident_log import (
    IncidentLog,
    STATUS_CLOSED,
    STATUS_OPEN,
    ZERO_DIGEST,
)


class TestIncidentLog(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "incidents.jsonl")

    def test_missing_file_replay_empty(self):
        log = IncidentLog(self.path)
        self.assertEqual(log.replay(), [])

    def test_open_then_status_open(self):
        log = IncidentLog(self.path)
        log.open("INC-1", "high", "disk full")
        self.assertEqual(log.status("INC-1"), STATUS_OPEN)

    def test_open_close_lifecycle_transitions_to_closed(self):
        log = IncidentLog(self.path)
        log.open("INC-1", "high", "disk full")
        self.assertEqual(log.status("INC-1"), STATUS_OPEN)
        log.close("INC-1", "cleared cache")
        self.assertEqual(log.status("INC-1"), STATUS_CLOSED)

    def test_reopen_identical_after_close_is_idempotent_noop(self):
        log = IncidentLog(self.path)
        log.open("INC-1", "low", "first")
        log.close("INC-1", "fixed")
        log.open("INC-1", "low", "first")
        # identical re-open is absorbed: no new event, status stays closed.
        self.assertEqual(log.status("INC-1"), STATUS_CLOSED)
        self.assertEqual(len(log.replay()), 2)

    def test_status_unknown_id_raises_keyerror(self):
        log = IncidentLog(self.path)
        with self.assertRaises(KeyError):
            log.status("NOPE")

    def test_close_unknown_id_raises_keyerror(self):
        log = IncidentLog(self.path)
        with self.assertRaises(KeyError):
            log.close("NOPE", "resolution")

    def test_replay_contains_open_and_close_in_order(self):
        log = IncidentLog(self.path)
        log.open("INC-1", "high", "disk full")
        log.close("INC-1", "cleared cache")
        events = log.replay()
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["type"], "open")
        self.assertEqual(events[1]["type"], "close")
        self.assertEqual(events[0]["incident_id"], "INC-1")
        self.assertEqual(events[1]["incident_id"], "INC-1")

    def test_idempotent_open_no_duplicate(self):
        log = IncidentLog(self.path)
        eid1 = log.open("INC-1", "high", "disk full")
        eid2 = log.open("INC-1", "high", "disk full")
        self.assertEqual(eid1, eid2)
        self.assertEqual(len(log.replay()), 1)

    def test_idempotent_close_no_duplicate(self):
        log = IncidentLog(self.path)
        log.open("INC-1", "high", "disk full")
        log.close("INC-1", "cleared cache")
        log.close("INC-1", "cleared cache")
        self.assertEqual(len(log.replay()), 2)

    def test_idempotent_after_reload(self):
        log = IncidentLog(self.path)
        log.open("INC-1", "high", "disk full")
        reloaded = IncidentLog(self.path)
        reloaded.open("INC-1", "high", "disk full")
        self.assertEqual(len(reloaded.replay()), 1)

    def test_reopen_different_detail_raises_valueerror(self):
        log = IncidentLog(self.path)
        log.open("INC-1", "high", "disk full")
        with self.assertRaises(ValueError):
            log.open("INC-1", "high", "different detail")

    def test_persistence_across_reload(self):
        log = IncidentLog(self.path)
        log.open("INC-1", "high", "disk full")
        log.close("INC-1", "cleared cache")
        reloaded = IncidentLog(self.path)
        self.assertEqual(reloaded.status("INC-1"), STATUS_CLOSED)
        self.assertEqual(len(reloaded.replay()), 2)

    def test_status_does_not_mutate_state(self):
        log = IncidentLog(self.path)
        log.open("INC-1", "high", "disk full")
        before = len(log.replay())
        for _ in range(3):
            self.assertEqual(log.status("INC-1"), STATUS_OPEN)
        self.assertEqual(len(log.replay()), before)

    def test_replay_returns_independent_copies(self):
        log = IncidentLog(self.path)
        log.open("INC-1", "high", "disk full")
        events = log.replay()
        events[0]["detail"] = "TAMPERED"
        self.assertEqual(log.replay()[0]["detail"], "disk full")

    def test_first_event_prev_is_zero_digest(self):
        log = IncidentLog(self.path)
        log.open("INC-1", "high", "disk full")
        self.assertEqual(log.replay()[0]["prev"], ZERO_DIGEST)

    def test_multiple_incidents_independent_status(self):
        log = IncidentLog(self.path)
        log.open("INC-1", "high", "a")
        log.open("INC-2", "low", "b")
        log.close("INC-1", "resolved")
        self.assertEqual(log.status("INC-1"), STATUS_CLOSED)
        self.assertEqual(log.status("INC-2"), STATUS_OPEN)


if __name__ == "__main__":
    unittest.main()

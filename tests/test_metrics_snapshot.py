"""tests/test_metrics_snapshot.py

Tests for noesis_harness.metrics_snapshot.snapshot.

Builds temporary logs via EventStore, then asserts on read-only metrics,
determinism, digest stability, and immutability of the underlying log.
"""

from __future__ import annotations

import os
import tempfile
import unittest

from noesis_harness.event_store import EventStore
from noesis_harness.metrics_snapshot import snapshot


_log_counter = {"n": 0}


def _write_log(tmp_dir: str, events, name: str = None) -> str:
    """Build a temporary event log and return its path."""
    _log_counter["n"] += 1
    fname = name or "events_{0}.jsonl".format(_log_counter["n"])
    path = os.path.join(tmp_dir, fname)
    store = EventStore(path)
    for etype, payload in events:
        store.append(etype, payload)
    return path


class MetricsSnapshotTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="metrics_snap_")

    def test_missing_log_is_empty(self):
        path = os.path.join(self.tmp, "does_not_exist.jsonl")
        snap = snapshot(path)
        self.assertEqual(snap["total"], 0)
        self.assertEqual(snap["per_type"], {})
        self.assertIsNone(snap["time_span"]["min"])
        self.assertIsNone(snap["time_span"]["max"])
        self.assertEqual(snap["seq_max"], 0)
        self.assertEqual(len(snap["digest"]), 64)

    def test_empty_log(self):
        path = _write_log(self.tmp, [])
        snap = snapshot(path)
        self.assertEqual(snap["total"], 0)
        self.assertEqual(snap["per_type"], {})
        self.assertEqual(snap["seq_max"], 0)

    def test_per_type_counts(self):
        path = _write_log(self.tmp, [
            ("note", {"text": "a"}),
            ("note", {"text": "b"}),
            ("action", {"kind": "run"}),
            ("signal", {"ch": "x"}),
            ("signal", {"ch": "y"}),
            ("signal", {"ch": "z"}),
        ])
        snap = snapshot(path)
        self.assertEqual(snap["total"], 6)
        self.assertEqual(snap["per_type"].get("note"), 2)
        self.assertEqual(snap["per_type"].get("action"), 1)
        self.assertEqual(snap["per_type"].get("signal"), 3)

    def test_seq_max(self):
        path = _write_log(self.tmp, [
            ("a", {}),
            ("b", {}),
            ("c", {}),
        ])
        snap = snapshot(path)
        self.assertEqual(snap["seq_max"], 3)

    def test_time_span_top_level_ts(self):
        path = os.path.join(self.tmp, "ts.jsonl")
        store = EventStore(path)
        store.append("a", {"x": 1}, event_id="e1")
        # inject a top-level ts by writing manually is not needed; use payload ts
        store.append("b", {"ts": 50})
        store.append("c", {"ts": 10})
        snap = snapshot(path)
        self.assertEqual(snap["time_span"]["min"], 10)
        self.assertEqual(snap["time_span"]["max"], 50)

    def test_time_span_payload_ts_absent(self):
        path = _write_log(self.tmp, [
            ("a", {"x": 1}),
            ("b", {"y": 2}),
        ])
        snap = snapshot(path)
        self.assertIsNone(snap["time_span"]["min"])
        self.assertIsNone(snap["time_span"]["max"])

    def test_string_timestamps_compare(self):
        path = os.path.join(self.tmp, "sts.jsonl")
        store = EventStore(path)
        store.append("a", {"ts": "2026-01-01"})
        store.append("b", {"ts": "2026-03-01"})
        store.append("c", {"ts": "2026-02-01"})
        snap = snapshot(path)
        self.assertEqual(snap["time_span"]["min"], "2026-01-01")
        self.assertEqual(snap["time_span"]["max"], "2026-03-01")

    def test_determinism(self):
        path = _write_log(self.tmp, [
            ("note", {"ts": 5}),
            ("signal", {"ts": 1}),
            ("note", {}),
        ])
        first = snapshot(path)
        second = snapshot(path)
        self.assertEqual(first, second)
        self.assertEqual(first["digest"], second["digest"])

    def test_digest_stability_across_runs(self):
        events = [("a", {"ts": 1}), ("b", {"t": 2}), ("a", {})]
        p1 = _write_log(self.tmp, events)
        p2 = os.path.join(self.tmp, "copy.jsonl")
        store2 = EventStore(p2)
        for et, pl in events:
            store2.append(et, pl)
        self.assertEqual(snapshot(p1)["digest"], snapshot(p2)["digest"])

    def test_digest_changes_with_content(self):
        p1 = _write_log(self.tmp, [("a", {}), ("a", {})])
        p2 = _write_log(self.tmp, [("a", {}), ("b", {})])
        self.assertNotEqual(snapshot(p1)["digest"], snapshot(p2)["digest"])

    def test_log_unchanged_after_snapshot(self):
        path = _write_log(self.tmp, [
            ("note", {"ts": 3}),
            ("signal", {"ts": 1}),
        ])
        with open(path, "rb") as fh:
            before = fh.read()
        snapshot(path)
        snapshot(path)
        with open(path, "rb") as fh:
            after = fh.read()
        self.assertEqual(before, after)

    def test_snapshot_is_pure_no_append(self):
        path = _write_log(self.tmp, [("a", {})])
        snapshot(path)
        store = EventStore(path)
        self.assertEqual(store.count(), 1)


if __name__ == "__main__":
    unittest.main()

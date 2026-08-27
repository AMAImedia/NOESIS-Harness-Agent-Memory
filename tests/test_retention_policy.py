"""tests/test_retention_policy.py

Tests for noesis_harness.retention_policy.evaluate (read-only, stdlib-only).

Covers: no expired, some expired by age, keep_types override, missing file,
determinism, read-only guarantee, and the edge case max_age_sec == 0.
"""

from __future__ import annotations

import os
import tempfile
import time
import unittest

from noesis_harness.event_store import EventStore
from noesis_harness.retention_policy import evaluate, _event_timestamp


def _build_log(records):
    """Write a JSONL event log from `records` = list of (type, ts, seq) tuples.

    Returns the path to the written log file in a temp dir.
    """
    fd, path = tempfile.mkstemp(suffix=".jsonl", prefix="retention_")
    os.close(fd)
    store = EventStore(path)
    for etype, ts, seq in records:
        store.append(etype, {"ts": ts}, event_id="evt-%d" % seq)
    return path


def _mtime(path):
    return os.stat(path).st_mtime_ns


class RetentionPolicyTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="retention_test_")
        self.now = 1_000_000.0

    def tearDown(self):
        for root, _dirs, files in os.walk(self.tmp):
            for name in files:
                os.remove(os.path.join(root, name))
        os.rmdir(self.tmp)

    def _path(self, name):
        return os.path.join(self.tmp, name)

    def test_no_expired_when_all_recent(self):
        path = self._path("recent.jsonl")
        store = EventStore(path)
        for i in range(5):
            store.append("msg", {"ts": self.now - i}, event_id="e%d" % i)
        result = evaluate(path, {"max_age_sec": 3600, "keep_types": []}, now=self.now)
        self.assertEqual(result["expired"], [])
        self.assertEqual(result["retained_count"], 5)
        self.assertTrue(result["compliant"])

    def test_some_expired_by_age(self):
        path = self._path("mixed.jsonl")
        store = EventStore(path)
        old_ts = self.now - 10000
        new_ts = self.now - 10
        store.append("old", {"ts": old_ts}, event_id="old1")
        store.append("old", {"ts": old_ts}, event_id="old2")
        store.append("new", {"ts": new_ts}, event_id="new1")
        result = evaluate(path, {"max_age_sec": 3600, "keep_types": []}, now=self.now)
        self.assertEqual(result["expired"], [1, 2])
        self.assertEqual(result["retained_count"], 1)
        self.assertFalse(result["compliant"])

    def test_keep_types_override(self):
        path = self._path("keep.jsonl")
        store = EventStore(path)
        store.append("audit", {"ts": self.now - 100000}, event_id="a1")
        store.append("log", {"ts": self.now - 100000}, event_id="l1")
        result = evaluate(
            path,
            {"max_age_sec": 3600, "keep_types": ["audit"]},
            now=self.now,
        )
        self.assertEqual(result["expired"], [2])
        self.assertEqual(result["retained_count"], 1)
        self.assertFalse(result["compliant"])

    def test_missing_file_returns_compliant(self):
        missing = self._path("does_not_exist.jsonl")
        self.assertFalse(os.path.exists(missing))
        result = evaluate(missing, {"max_age_sec": 3600, "keep_types": []}, now=self.now)
        self.assertEqual(result, {"expired": [], "retained_count": 0, "compliant": True})

    def test_determinism(self):
        path = self._path("det.jsonl")
        store = EventStore(path)
        for i in range(10):
            store.append("e", {"ts": self.now - (i * 1000)}, event_id="d%d" % i)
        policy = {"max_age_sec": 2500, "keep_types": []}
        first = evaluate(path, policy, now=self.now)
        second = evaluate(path, policy, now=self.now)
        self.assertEqual(first, second)
        self.assertEqual(first["expired"], [4, 5, 6, 7, 8, 9, 10])

    def test_read_only_does_not_modify_log(self):
        path = self._path("ro.jsonl")
        store = EventStore(path)
        for i in range(4):
            store.append("e", {"ts": self.now - 100000}, event_id="r%d" % i)
        size_before = os.path.getsize(path)
        mtime_before = _mtime(path)
        time.sleep(0.001)
        evaluate(path, {"max_age_sec": 10, "keep_types": []}, now=self.now)
        self.assertEqual(os.path.getsize(path), size_before)
        self.assertEqual(_mtime(path), mtime_before)

    def test_max_age_zero_expires_dated(self):
        path = self._path("zero.jsonl")
        store = EventStore(path)
        store.append("old", {"ts": self.now - 5}, event_id="z1")
        store.append("old", {"ts": self.now - 1}, event_id="z2")
        result = evaluate(path, {"max_age_sec": 0, "keep_types": []}, now=self.now)
        self.assertEqual(result["expired"], [1, 2])
        self.assertEqual(result["retained_count"], 0)
        self.assertFalse(result["compliant"])

    def test_max_age_zero_keeps_future_timestamp(self):
        path = self._path("future.jsonl")
        store = EventStore(path)
        store.append("old", {"ts": self.now + 500}, event_id="f1")
        result = evaluate(path, {"max_age_sec": 0, "keep_types": []}, now=self.now)
        self.assertEqual(result["expired"], [])
        self.assertEqual(result["retained_count"], 1)
        self.assertTrue(result["compliant"])

    def test_undated_events_retained(self):
        path = self._path("undated.jsonl")
        store = EventStore(path)
        store.append("mystery", {}, event_id="u1")
        store.append("mystery", {}, event_id="u2")
        result = evaluate(path, {"max_age_sec": 0, "keep_types": []}, now=self.now)
        self.assertEqual(result["expired"], [])
        self.assertEqual(result["retained_count"], 2)
        self.assertTrue(result["compliant"])

    def test_event_timestamp_resolution(self):
        self.assertIsNone(_event_timestamp({"type": "x"}))
        self.assertEqual(_event_timestamp({"ts": 42.0, "type": "x"}), 42.0)
        self.assertEqual(_event_timestamp({"type": "x", "payload": {"ts": 7}}), 7.0)
        self.assertIsNone(_event_timestamp({"type": "x", "payload": {"ts": "soon"}}))

    def test_invalid_max_age_raises(self):
        path = self._path("bad.jsonl")
        store = EventStore(path)
        store.append("e", {"ts": self.now}, event_id="b1")
        with self.assertRaises(ValueError):
            evaluate(path, {"max_age_sec": -1, "keep_types": []}, now=self.now)
        with self.assertRaises(ValueError):
            evaluate(path, {"max_age_sec": "forever", "keep_types": []}, now=self.now)

    def test_keep_types_empty_still_expires(self):
        path = self._path("nokeep.jsonl")
        store = EventStore(path)
        store.append("any", {"ts": self.now - 9999}, event_id="k1")
        result = evaluate(path, {"max_age_sec": 1, "keep_types": []}, now=self.now)
        self.assertEqual(result["expired"], [1])
        self.assertFalse(result["compliant"])


if __name__ == "__main__":
    unittest.main()

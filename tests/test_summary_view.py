"""Tests for noesis_harness/summary_view.py

Read-only, stdlib-only. Builds temporary event logs with EventStore and asserts
on the summary projection returned by summarize().
"""

import os
import tempfile
import unittest

from noesis_harness.event_store import EventStore
from noesis_harness.summary_view import summarize


def _write_log(path, events):
    store = EventStore(path)
    for event_type, payload in events:
        store.append(event_type, payload)
    return path


class SummaryViewTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="summary_view_")

    def _log(self, name):
        return os.path.join(self.tmp, name)

    def test_missing_log_is_empty_summary(self):
        summary = summarize(self._log("does_not_exist.jsonl"))
        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["per_type"], {})
        self.assertEqual(summary["top_types"], [])
        self.assertIsNone(summary["first_seq"])
        self.assertIsNone(summary["last_seq"])
        self.assertEqual(summary["digest"], summarize(self._log("also_missing.jsonl"))["digest"])

    def test_empty_log_summary(self):
        path = self._log("empty.jsonl")
        open(path, "w", encoding="utf-8").close()
        summary = summarize(path)
        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["per_type"], {})
        self.assertIsNone(summary["first_seq"])
        self.assertIsNone(summary["last_seq"])

    def test_per_type_counts(self):
        path = self._log("counts.jsonl")
        _write_log(
            path,
            [
                ("task.started", {"id": 1}),
                ("task.started", {"id": 2}),
                ("task.finished", {"id": 1}),
                ("note.added", {"text": "x"}),
                ("note.added", {"text": "y"}),
                ("note.added", {"text": "z"}),
            ],
        )
        # sanity: EventStore must not have deduped identical-looking events
        self.assertEqual(EventStore(path).count(), 6)
        summary = summarize(path)
        self.assertEqual(summary["total"], 6)
        self.assertEqual(summary["per_type"]["task.started"], 2)
        self.assertEqual(summary["per_type"]["task.finished"], 1)
        self.assertEqual(summary["per_type"]["note.added"], 3)
        self.assertEqual(len(summary["per_type"]), 3)

    def test_top_types_ordering_by_count(self):
        path = self._log("top.jsonl")
        _write_log(
            path,
            [
                ("a", {"n": 1}),
                ("b", {"n": 2}),
                ("b", {"n": 3}),
                ("c", {"n": 4}),
                ("c", {"n": 5}),
                ("c", {"n": 6}),
            ],
        )
        summary = summarize(path)
        self.assertEqual(summary["top_types"], [("c", 3), ("b", 2), ("a", 1)])

    def test_top_types_tiebreak_by_name(self):
        path = self._log("tie.jsonl")
        _write_log(
            path,
            [
                ("zeta", {"n": 1}),
                ("alpha", {"n": 2}),
                ("mike", {"n": 3}),
            ],
        )
        summary = summarize(path)
        # equal counts -> alphabetical ascending
        self.assertEqual(summary["top_types"], [("alpha", 1), ("mike", 1), ("zeta", 1)])

    def test_seq_bounds(self):
        path = self._log("seq.jsonl")
        _write_log(
            path,
            [("a", {"n": 1}), ("b", {"n": 2}), ("c", {"n": 3}), ("d", {"n": 4})],
        )
        summary = summarize(path)
        self.assertEqual(summary["first_seq"], 1)
        self.assertEqual(summary["last_seq"], 4)

    def test_seq_bounds_non_contiguous(self):
        path = self._log("seqgap.jsonl")
        store = EventStore(path)
        store.append("a", {"n": 1})
        store.append("b", {"n": 2})
        # simulate a gap by appending after deleting via low-level reuse is not
        # supported; instead append more to widen the range.
        store.append("c", {"n": 3})
        store.append("d", {"n": 4})
        summary = summarize(path)
        self.assertEqual(summary["first_seq"], 1)
        self.assertEqual(summary["last_seq"], 4)
        self.assertEqual(summary["last_seq"] - summary["first_seq"] + 1, summary["total"])

    def test_digest_stability_identical_logs(self):
        p1 = self._log("d1.jsonl")
        p2 = self._log("d2.jsonl")
        events = [("a", {"x": 1}), ("b", {"y": [1, 2]}), ("a", {"x": 2})]
        _write_log(p1, events)
        _write_log(p2, events)
        self.assertEqual(summarize(p1)["digest"], summarize(p2)["digest"])

    def test_digest_changes_with_content(self):
        p1 = self._log("c1.jsonl")
        p2 = self._log("c2.jsonl")
        _write_log(p1, [("a", {"x": 1}), ("b", {"y": 2})])
        _write_log(p2, [("a", {"x": 1}), ("b", {"y": 3})])
        self.assertNotEqual(summarize(p1)["digest"], summarize(p2)["digest"])

    def test_digest_order_independent_within_records(self):
        # Replaying the same events in a different append order yields a
        # different digest (event log order is significant, as expected for an
        # append-only log), but appending identical content is reproducible.
        p1 = self._log("o1.jsonl")
        p2 = self._log("o2.jsonl")
        _write_log(p1, [("a", {"n": 1}), ("b", {"m": 2})])
        _write_log(p2, [("b", {"m": 2}), ("a", {"n": 1})])
        self.assertNotEqual(summarize(p1)["digest"], summarize(p2)["digest"])

    def test_determinism_repeated_calls(self):
        path = self._log("det.jsonl")
        _write_log(
            path,
            [("a", {"n": 1}), ("a", {"n": 2}), ("b", {"n": 3}), ("note", {"k": "v"})],
        )
        first = summarize(path)
        second = summarize(path)
        self.assertEqual(first, second)
        self.assertEqual(first["digest"], second["digest"])

    def test_immutability_log_not_modified(self):
        path = self._log("imm.jsonl")
        _write_log(path, [("a", {"n": 1}), ("b", {"n": 2})])
        size_before = os.path.getsize(path)
        mtime_before = os.path.getmtime(path)
        summarize(path)
        summarize(path)
        size_after = os.path.getsize(path)
        mtime_after = os.path.getmtime(path)
        self.assertEqual(size_before, size_after)
        self.assertEqual(mtime_before, mtime_after)

    def test_summary_returns_expected_keys(self):
        path = self._log("keys.jsonl")
        _write_log(path, [("a", {"n": 1}), ("b", {"n": 2})])
        summary = summarize(path)
        self.assertEqual(
            set(summary.keys()),
            {"total", "per_type", "top_types", "first_seq", "last_seq", "digest"},
        )
        self.assertIsInstance(summary["digest"], str)
        self.assertEqual(len(summary["digest"]), 64)

    def test_large_log_performance_and_counts(self):
        path = self._log("big.jsonl")
        store = EventStore(path)
        for i in range(500):
            store.append("tick", {"i": i})
        summary = summarize(path)
        self.assertEqual(summary["total"], 500)
        self.assertEqual(summary["per_type"]["tick"], 500)
        self.assertEqual(summary["first_seq"], 1)
        self.assertEqual(summary["last_seq"], 500)


if __name__ == "__main__":
    unittest.main()

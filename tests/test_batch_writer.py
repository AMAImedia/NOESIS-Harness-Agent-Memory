"""tests/test_batch_writer.py

Unit tests for noesis_harness.batch_writer.BatchWriter.

Stdlib only. Exercises append semantics, idempotency, counting, file creation,
determinism, and corruption-safety against the append-only EventStore.
"""

from __future__ import annotations

import os
import tempfile
import unittest

from noesis_harness.batch_writer import BatchWriter


def _tmp_path() -> str:
    fd, path = tempfile.mkstemp(suffix=".jsonl", prefix="bw_test_")
    os.close(fd)
    os.remove(path)
    return path


class BatchWriterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.path = _tmp_path()

    def tearDown(self) -> None:
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_write_many_appends(self) -> None:
        w = BatchWriter(self.path)
        ids = w.write_many([("note", {"x": 1}), ("note", {"x": 2})])
        self.assertEqual(len(ids), 2)
        self.assertEqual(w.count(), 2)
        self.assertTrue(os.path.exists(self.path))

    def test_idempotent_reappend(self) -> None:
        w1 = BatchWriter(self.path)
        w1.write_many([("note", {"x": 1}), ("note", {"x": 2})])
        w2 = BatchWriter(self.path)
        w2.write_many([("note", {"x": 1}), ("note", {"x": 2})])
        self.assertEqual(w2.count(), 2)

    def test_count_matches_appended(self) -> None:
        w = BatchWriter(self.path)
        batch = [("a", i) for i in range(7)]
        w.write_many(batch)
        self.assertEqual(w.count(), 7)

    def test_empty_list_noop(self) -> None:
        w = BatchWriter(self.path)
        ids = w.write_many([])
        self.assertEqual(ids, [])
        self.assertEqual(w.count(), 0)
        self.assertFalse(w.exists())

    def test_missing_file_created(self) -> None:
        self.assertFalse(os.path.exists(self.path))
        w = BatchWriter(self.path)
        w.write_many([("note", {"v": 1})])
        self.assertTrue(os.path.exists(self.path))
        self.assertEqual(w.count(), 1)

    def test_determinism_same_ids(self) -> None:
        w1 = BatchWriter(self.path)
        ids_a = w1.write_many([("note", {"k": "v"})])
        w2 = BatchWriter(self.path)
        ids_b = w2.write_many([("note", {"k": "v"})])
        self.assertEqual(ids_a, ids_b)

    def test_partial_overlap_idempotent(self) -> None:
        w1 = BatchWriter(self.path)
        w1.write_many([("note", {"x": 1}), ("note", {"x": 2})])
        w2 = BatchWriter(self.path)
        w2.write_many([("note", {"x": 2}), ("note", {"x": 3})])
        self.assertEqual(w2.count(), 3)

    def test_distinct_types_stay_distinct(self) -> None:
        w = BatchWriter(self.path)
        w.write_many([("a", {"v": 1}), ("b", {"v": 1})])
        self.assertEqual(w.count(), 2)

    def test_no_corruption_append_only(self) -> None:
        w = BatchWriter(self.path)
        w.write_many([("note", {"x": 1}), ("note", {"x": 2})])
        with open(self.path, "r", encoding="utf-8") as fh:
            lines = [ln for ln in fh.read().splitlines() if ln.strip()]
        self.assertEqual(len(lines), 2)
        for ln in lines:
            self.assertIn("event_id", ln)
            self.assertIn("seq", ln)

    def test_reload_preserves_count(self) -> None:
        w1 = BatchWriter(self.path)
        w1.write_many([("note", {"x": 1}), ("note", {"x": 2}), ("note", {"x": 3})])
        w2 = BatchWriter(self.path)
        self.assertEqual(w2.count(), 3)

    def test_large_batch(self) -> None:
        w = BatchWriter(self.path)
        batch = [("tick", {"i": i}) for i in range(100)]
        w.write_many(batch)
        self.assertEqual(w.count(), 100)
        w.write_many(batch)
        self.assertEqual(w.count(), 100)

    def test_payload_order_preserved_in_store(self) -> None:
        w = BatchWriter(self.path)
        w.write_many([("note", {"n": 1}), ("note", {"n": 2}), ("note", {"n": 3})])
        seqs = [rec["seq"] for rec in w._store.iter_events()]
        self.assertEqual(seqs, [1, 2, 3])


if __name__ == "__main__":
    unittest.main()

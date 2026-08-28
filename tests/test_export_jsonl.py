"""tests/test_export_jsonl.py

Unit tests for noesis_harness.export_jsonl.

Covers: export all, filter by type, out file written, count matches, empty log
-> empty file, read-only guarantee on source, missing source handled, and
determinism. Stdlib only.
"""

from __future__ import annotations

import builtins
import json
import os
import tempfile
import unittest

from noesis_harness.export_jsonl import export


def _write_log(path: str, records: list) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _make_sample() -> list:
    return [
        {"event_id": "a1", "type": "task.started", "payload": {"x": 1}, "seq": 1},
        {"event_id": "a2", "type": "task.completed", "payload": {"x": 2}, "seq": 2},
        {"event_id": "a3", "type": "task.started", "payload": {"x": 3}, "seq": 3},
    ]


class ExportJsonlTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.src = os.path.join(self.tmp, "events.jsonl")
        self.out = os.path.join(self.tmp, "out", "export.jsonl")

    def _read_out(self) -> list:
        with open(self.out, "r", encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def test_export_all(self):
        _write_log(self.src, _make_sample())
        n = export(self.src, self.out)
        self.assertEqual(n, 3)
        self.assertEqual(len(self._read_out()), 3)

    def test_filter_by_type(self):
        _write_log(self.src, _make_sample())
        n = export(self.src, self.out, filter_type="task.started")
        self.assertEqual(n, 2)
        out = self._read_out()
        self.assertTrue(all(r["type"] == "task.started" for r in out))

    def test_out_file_written(self):
        _write_log(self.src, _make_sample())
        self.assertFalse(os.path.exists(self.out))
        export(self.src, self.out)
        self.assertTrue(os.path.exists(self.out))

    def test_count_matches_written_lines(self):
        recs = _make_sample()
        _write_log(self.src, recs)
        n = export(self.src, self.out)
        self.assertEqual(n, len(recs))
        self.assertEqual(n, len(self._read_out()))

    def test_empty_log_produces_empty_file(self):
        _write_log(self.src, [])
        n = export(self.src, self.out)
        self.assertEqual(n, 0)
        self.assertTrue(os.path.exists(self.out))
        self.assertEqual(os.path.getsize(self.out), 0)

    def test_missing_source_creates_empty_file(self):
        missing = os.path.join(self.tmp, "does_not_exist.jsonl")
        self.assertFalse(os.path.exists(missing))
        n = export(missing, self.out)
        self.assertEqual(n, 0)
        self.assertTrue(os.path.exists(self.out))
        self.assertEqual(os.path.getsize(self.out), 0)

    def test_read_only_guarantee_on_source(self):
        _write_log(self.src, _make_sample())
        with open(self.src, "rb") as fh:
            before = fh.read()
        mtime_before = os.path.getmtime(self.src)
        size_before = os.path.getsize(self.src)

        real_open = builtins.open
        captured = []

        def spy(path, mode="r", *args, **kwargs):
            if path == self.src:
                self.assertIn(mode, ("rb", "r"), "source opened for writing")
                captured.append(mode)
            return real_open(path, mode, *args, **kwargs)

        builtins.open = spy
        try:
            export(self.src, self.out)
        finally:
            builtins.open = real_open

        self.assertTrue(captured, "source was never opened")
        with open(self.src, "rb") as fh:
            after = fh.read()
        self.assertEqual(before, after)
        self.assertEqual(os.path.getsize(self.src), size_before)
        self.assertEqual(os.path.getmtime(self.src), mtime_before)

    def test_determinism(self):
        recs = _make_sample()
        _write_log(self.src, recs)
        out1 = os.path.join(self.tmp, "o1.jsonl")
        out2 = os.path.join(self.tmp, "o2.jsonl")
        export(self.src, out1)
        export(self.src, out2)
        with open(out1, "rb") as a, open(out2, "rb") as b:
            self.assertEqual(a.read(), b.read())

    def test_determinism_preserves_seq_order(self):
        recs = [
            {"event_id": "z", "type": "t", "payload": {}, "seq": 3},
            {"event_id": "y", "type": "t", "payload": {}, "seq": 1},
            {"event_id": "x", "type": "t", "payload": {}, "seq": 2},
        ]
        _write_log(self.src, recs)
        export(self.src, self.out)
        seqs = [r["seq"] for r in self._read_out()]
        self.assertEqual(seqs, [1, 2, 3])

    def test_filter_matches_exact_type_only(self):
        recs = [
            {"event_id": "1", "type": "task.started", "payload": {}, "seq": 1},
            {"event_id": "2", "type": "task.started.v2", "payload": {}, "seq": 2},
            {"event_id": "3", "type": "task", "payload": {}, "seq": 3},
        ]
        _write_log(self.src, recs)
        n = export(self.src, self.out, filter_type="task.started")
        self.assertEqual(n, 1)

    def test_blank_lines_ignored(self):
        recs = _make_sample()
        with open(self.src, "w", encoding="utf-8") as fh:
            for rec in recs:
                fh.write(json.dumps(rec) + "\n\n")
        n = export(self.src, self.out)
        self.assertEqual(n, 3)
        self.assertEqual(len(self._read_out()), 3)


if __name__ == "__main__":
    unittest.main()

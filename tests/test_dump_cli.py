"""Tests for noesis_harness/dump_cli.py

Read-only JSON-lines dump of the event log. Verifies: temp log setup, --limit
truncation, --type filter, --out file written, one JSON object per line, exit
code 0, and that the event log is never mutated (read-only). Stdlib only.
"""

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

from noesis_harness import dump_cli
from noesis_harness import event_store


def _append_events(path, items):
    """items: list of (event_type, payload). Writes the log via EventStore."""
    store = event_store.EventStore(path)
    for etype, payload in items:
        store.append(etype, payload)


class DumpCliTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="dump_cli_")
        self.log = os.path.join(self.tmp, "events.jsonl")
        _append_events(
            self.log,
            [
                ("note", {"text": "alpha"}),
                ("task", {"text": "beta"}),
                ("note", {"text": "gamma"}),
                ("task", {"text": "delta"}),
                ("note", {"text": "epsilon"}),
            ],
        )

    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        code = 0
        with redirect_stdout(out), redirect_stderr(err):
            try:
                code = dump_cli.main(argv)
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 0
        return code, out.getvalue(), err.getvalue()

    def test_exit_code_zero_on_success(self):
        code, _, _ = self._run(["--events", self.log])
        self.assertEqual(code, 0)

    def test_one_json_object_per_line(self):
        code, out, _ = self._run(["--events", self.log])
        self.assertEqual(code, 0)
        lines = [ln for ln in out.splitlines() if ln.strip()]
        self.assertEqual(len(lines), 5)
        for ln in lines:
            obj = json.loads(ln)
            self.assertIn("event_id", obj)
            self.assertIn("type", obj)
            self.assertIn("seq", obj)

    def test_limit_truncation(self):
        code, out, _ = self._run(["--events", self.log, "--limit", "2"])
        self.assertEqual(code, 0)
        lines = [ln for ln in out.splitlines() if ln.strip()]
        self.assertEqual(len(lines), 2)
        # first two events in append order are emitted
        first = json.loads(lines[0])
        self.assertEqual(first["type"], "note")
        self.assertEqual(first["seq"], 1)

    def test_type_filter(self):
        code, out, _ = self._run(["--events", self.log, "--type", "task"])
        self.assertEqual(code, 0)
        lines = [ln for ln in out.splitlines() if ln.strip()]
        self.assertEqual(len(lines), 2)
        for ln in lines:
            self.assertEqual(json.loads(ln)["type"], "task")

    def test_type_filter_no_match(self):
        code, out, _ = self._run(["--events", self.log, "--type", "missing"])
        self.assertEqual(code, 0)
        lines = [ln for ln in out.splitlines() if ln.strip()]
        self.assertEqual(len(lines), 0)

    def test_out_file_written(self):
        out_path = os.path.join(self.tmp, "dump.jsonl")
        code, out, _ = self._run(
            ["--events", self.log, "--out", out_path]
        )
        self.assertEqual(code, 0)
        self.assertEqual(out, "")  # nothing on stdout when --out is given
        self.assertTrue(os.path.exists(out_path))
        with open(out_path, "r", encoding="utf-8") as fh:
            content = fh.read()
        lines = [ln for ln in content.splitlines() if ln.strip()]
        self.assertEqual(len(lines), 5)
        self.assertEqual(json.loads(lines[-1])["seq"], 5)

    def test_read_only_guarantee(self):
        with open(self.log, "rb") as fh:
            before = fh.read()
        for _ in range(3):
            self._run(["--events", self.log, "--limit", "3"])
            self._run(["--events", self.log, "--type", "note"])
            self._run(["--events", self.log, "--out",
                       os.path.join(self.tmp, "x.jsonl")])
        with open(self.log, "rb") as fh:
            after = fh.read()
        self.assertEqual(before, after)

    def test_limit_and_type_combined(self):
        code, out, _ = self._run(
            ["--events", self.log, "--type", "note", "--limit", "1"]
        )
        self.assertEqual(code, 0)
        lines = [ln for ln in out.splitlines() if ln.strip()]
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["type"], "note")
        self.assertEqual(json.loads(lines[0])["seq"], 1)


if __name__ == "__main__":
    unittest.main()

"""tests/test_tail_cli.py

Read-only CLI tests for noesis_harness.tail_cli.

Stdlib only. Python 3.9+ compatible.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest

from noesis_harness import event_store, tail_cli


def _write_log(path: str, count: int) -> None:
    store = event_store.EventStore(path)
    for i in range(count):
        store.append("step", {"i": i}, event_id="evt-%d" % i)


def _run(*cli_args) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = tail_cli.main(list(cli_args))
    return rc, buf.getvalue()


class TailCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="tail_cli_")
        self.log = os.path.join(self.tmp, "events.jsonl")

    def test_truncation_keeps_last_n(self) -> None:
        _write_log(self.log, 50)
        rc, out = _run("--events", self.log, "--n", "5")
        self.assertEqual(rc, 0)
        lines = [l for l in out.splitlines() if l]
        self.assertEqual(len(lines), 5)
        last = json.loads(lines[-1])
        self.assertEqual(last["payload"]["i"], 49)
        self.assertEqual(last["seq"], 50)

    def test_full_log_when_n_exceeds_count(self) -> None:
        _write_log(self.log, 7)
        rc, out = _run("--events", self.log, "--n", "100")
        self.assertEqual(rc, 0)
        lines = [l for l in out.splitlines() if l]
        self.assertEqual(len(lines), 7)
        self.assertEqual(json.loads(lines[0])["payload"]["i"], 0)

    def test_n_zero_emits_nothing(self) -> None:
        _write_log(self.log, 10)
        rc, out = _run("--events", self.log, "--n", "0")
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), "")

    def test_json_shape_is_array_of_records(self) -> None:
        _write_log(self.log, 12)
        rc, out = _run("--events", self.log, "--n", "4", "--json")
        self.assertEqual(rc, 0)
        arr = json.loads(out.strip())
        self.assertIsInstance(arr, list)
        self.assertEqual(len(arr), 4)
        for rec in arr:
            self.assertIn("event_id", rec)
            self.assertIn("type", rec)
            self.assertIn("payload", rec)
            self.assertIn("seq", rec)
        self.assertEqual(arr[-1]["payload"]["i"], 11)

    def test_empty_log(self) -> None:
        _write_log(self.log, 0)
        rc, out = _run("--events", self.log)
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), "")

    def test_missing_log_is_empty(self) -> None:
        rc, out = _run("--events", os.path.join(self.tmp, "nope.jsonl"), "--n", "3")
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), "")

    def test_exit_code_zero(self) -> None:
        _write_log(self.log, 3)
        rc, _ = _run("--events", self.log, "--n", "2")
        self.assertEqual(rc, 0)

    def test_read_only_no_writes(self) -> None:
        _write_log(self.log, 9)
        before = os.path.getsize(self.log)
        with open(self.log, "rb") as fh:
            before_bytes = fh.read()
        _run("--events", self.log, "--n", "5")
        after = os.path.getsize(self.log)
        with open(self.log, "rb") as fh:
            after_bytes = fh.read()
        self.assertEqual(before, after)
        self.assertEqual(before_bytes, after_bytes)

    def test_deterministic_repeat(self) -> None:
        _write_log(self.log, 20)
        _, first = _run("--events", self.log, "--n", "6")
        _, second = _run("--events", self.log, "--n", "6")
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()

import builtins
import contextlib
import io
import json
import os
import sqlite3
import tempfile
import unittest

from noesis_harness import event_store
from noesis_harness import inspect_cli


def _make_event_log(path):
    store = event_store.EventStore(path)
    store.append("task.started", {"task": "a", "ts": 1.0})
    store.append("task.progress", {"task": "a", "ts": 2.0})
    store.append("task.done", {"task": "a", "ts": 3.0})
    return path


def _make_leases_db(path):
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE leases ("
        " task_key TEXT NOT NULL,"
        " holder TEXT NOT NULL,"
        " acquired_at REAL NOT NULL,"
        " expires_at REAL NOT NULL,"
        " status TEXT NOT NULL)"
    )
    conn.execute(
        "INSERT INTO leases (task_key, holder, acquired_at, expires_at, status)"
        " VALUES (?,?,?,?,?)",
        ("task-a", "agent-1", 100.0, 160.0, "active"),
    )
    conn.commit()
    conn.close()
    return path


class InspectCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.events = os.path.join(self.tmp, "events.jsonl")
        self.leases = os.path.join(self.tmp, "coord.sqlite")
        _make_event_log(self.events)
        _make_leases_db(self.leases)

    def tearDown(self):
        for p in (self.events, self.leases):
            if os.path.exists(p):
                os.remove(p)
        if os.path.isdir(self.tmp):
            try:
                os.rmdir(self.tmp)
            except OSError:
                pass

    def _run(self, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = inspect_cli.main(argv)
        return code, buf.getvalue()

    def test_metrics_view_returns_json_and_exit0(self):
        code, out = self._run(["--events", self.events, "--view", "metrics"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["total"], 3)
        self.assertIn("digest", data)

    def test_summary_view_returns_json_and_exit0(self):
        code, out = self._run(["--events", self.events, "--view", "summary"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIn("total", data)

    def test_leases_view_returns_json_and_exit0(self):
        code, out = self._run(["--leases", self.leases, "--view", "leases"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["scope"], "coordination")

    def test_read_only_no_mutation(self):
        with open(self.events, "rb") as fh:
            before = fh.read()
        for view in ("metrics", "summary"):
            code, _ = self._run(["--events", self.events, "--view", view])
            self.assertEqual(code, 0)
        with open(self.events, "rb") as fh:
            after = fh.read()
        self.assertEqual(before, after)

    def test_missing_events_arg_returns_exit2(self):
        code, _ = self._run(["--view", "metrics"])
        self.assertEqual(code, 2)

    def test_missing_leases_arg_returns_exit2(self):
        code, _ = self._run(["--view", "leases"])
        self.assertEqual(code, 2)

    def test_missing_dependency_path(self):
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "noesis_harness.metrics_snapshot":
                raise ImportError("noesis_harness.metrics_snapshot is unavailable")
            return real_import(name, *args, **kwargs)

        builtins.__import__ = fake_import
        try:
            code, out = self._run(["--events", self.events, "--view", "metrics"])
        finally:
            builtins.__import__ = real_import
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["view"], "metrics")
        self.assertEqual(data["error"], "missing dependency")

    def test_metrics_view_keys_present(self):
        code, out = self._run(["--events", self.events, "--view", "metrics"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        for key in ("total", "per_type", "time_span", "seq_max", "digest"):
            self.assertIn(key, data)


if __name__ == "__main__":
    unittest.main()

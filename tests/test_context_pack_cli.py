"""Tests for noesis_harness/context_pack_cli.py

Read-only CLI over recall_augment.rank_events. Verifies: --query returns ranked
context, --json shape, exit code 0, and that the event log is never mutated.
Imports recall_augment inside the function under test (main). Stdlib only.
"""

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

from noesis_harness import context_pack_cli
from noesis_harness import event_store


def _write_log(path, records):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(rec + "\n")


def _append_events(path, items):
    """items: list of (event_type, payload). Writes the log via EventStore."""
    store = event_store.EventStore(path)
    for etype, payload in items:
        store.append(etype, payload)


class ContextPackCliTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ctxpack_cli_")
        self.log = os.path.join(self.tmp, "events.jsonl")
        _append_events(
            self.log,
            [
                ("note", {"text": "deploy the blue service to production"}),
                ("note", {"text": "rollback the red service after the incident"}),
                ("task", {"text": "the blue service handles user authentication"}),
                ("note", {"text": "unrelated invoice total is forty two dollars"}),
            ],
        )

    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        code = 0
        with redirect_stdout(out), redirect_stderr(err):
            try:
                code = context_pack_cli.main(argv)
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 0
        return code, out.getvalue(), err.getvalue()

    def test_query_returns_ranked_markdown(self):
        code, out, _ = self._run(
            ["--events", self.log, "--query", "blue service production"]
        )
        self.assertEqual(code, 0)
        self.assertIn("# Context pack", out)
        self.assertIn("blue service", out)
        self.assertIn("```", out)

    def test_json_shape(self):
        code, out, _ = self._run(
            ["--events", self.log, "--query", "blue service", "--json"]
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["query"], "blue service")
        self.assertEqual(data["events"], self.log)
        self.assertEqual(data["count"], len(data["ranked"]))
        self.assertIsInstance(data["ranked"], list)
        if data["ranked"]:
            item = data["ranked"][0]
            for key in ("seq", "event_id", "type", "score", "snippet"):
                self.assertIn(key, item)

    def test_top_k_respected(self):
        code, out, _ = self._run(
            ["--events", self.log, "--query", "service", "--top-k", "2", "--json"]
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertLessEqual(data["count"], 2)

    def test_exit_code_zero_on_success(self):
        code, _, _ = self._run(["--events", self.log, "--query", "blue"])
        self.assertEqual(code, 0)

    def test_read_only_guarantee(self):
        with open(self.log, "rb") as fh:
            before = fh.read()
        for _ in range(3):
            self._run(["--events", self.log, "--query", "blue service", "--json"])
        with open(self.log, "rb") as fh:
            after = fh.read()
        self.assertEqual(before, after)

    def test_missing_events_returns_empty_exit_0(self):
        # recall_augment treats a missing log as empty (graceful, read-only).
        missing = os.path.join(self.tmp, "nope.jsonl")
        code, out, err = self._run(["--events", missing, "--query", "x", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["ranked"], [])
        self.assertEqual(data["count"], 0)

    def test_ranking_prefers_overlap(self):
        code, out, _ = self._run(
            ["--events", self.log, "--query", "blue service production", "--json"]
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertGreaterEqual(len(data["ranked"]), 1)
        top = data["ranked"][0]
        self.assertIn("blue service", top["snippet"])

    def test_recall_augment_imported_inside_function(self):
        # Force the in-function import to fail and ensure a clear message + code 3.
        import noesis_harness
        import sys

        submodule = "noesis_harness.recall_augment"
        saved_module = sys.modules.pop(submodule, None)
        saved_attr = getattr(noesis_harness, "recall_augment", None)
        if saved_attr is not None:
            delattr(noesis_harness, "recall_augment")
        sys.modules[submodule] = None  # marks the submodule import as failed
        try:
            code, _, err = self._run(["--events", self.log, "--query", "x"])
        finally:
            sys.modules.pop(submodule, None)
            if saved_module is not None:
                sys.modules[submodule] = saved_module
            if saved_attr is not None:
                setattr(noesis_harness, "recall_augment", saved_attr)
        self.assertEqual(code, 3)
        self.assertIn("recall_augment unavailable", err)

    def test_empty_query_json_shape(self):
        code, out, _ = self._run(["--events", self.log, "--query", "", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["count"], len(data["ranked"]))
        self.assertTrue(all(r["score"] == 0.0 for r in data["ranked"]))


if __name__ == "__main__":
    unittest.main()

"""Tests for benchmarks.bench_eventstore (stdlib only, no repo writes)."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from benchmarks import bench_eventstore


class TestBenchEventstore(unittest.TestCase):
    def test_replay_count_matches(self):
        n = 150
        result = bench_eventstore.bench(n)
        self.assertEqual(result["events"], n)
        self.assertTrue(result["passed"])
        from noesis_harness.event_store import EventStore

        tmp = tempfile.mkdtemp(prefix="noesis_tes_")
        log_path = os.path.join(tmp, "events.jsonl")
        bench_eventstore._build_store(log_path, n)
        replay_count = len(list(EventStore(log_path).iter_events()))
        self.assertEqual(replay_count, n)

    def test_default_passed_true(self):
        result = bench_eventstore.bench(75)
        self.assertTrue(result["passed"])
        self.assertGreaterEqual(result["append_sec"], 0.0)
        self.assertGreaterEqual(result["replay_sec"], 0.0)

    def test_main_returns_zero(self):
        self.assertEqual(bench_eventstore.main(["--events", "50"]), 0)

    def test_no_repo_writes(self):
        root_files_before = set(os.listdir(ROOT))
        bench_eventstore.main(["--events", "30"])
        root_files_after = set(os.listdir(ROOT))
        self.assertEqual(root_files_before, root_files_after)

    def test_only_temp_side_effects(self):
        tmp_before = set(os.listdir(tempfile.gettempdir()))
        bench_eventstore.main(["--events", "40"])
        tmp_after = set(os.listdir(tempfile.gettempdir()))
        new_entries = tmp_after - tmp_before
        self.assertTrue(
            any(n.startswith("noesis_bench_eventstore_") for n in new_entries)
        )

    def test_lazy_import(self):
        self.assertFalse(hasattr(bench_eventstore, "EventStore"))
        from noesis_harness.event_store import EventStore

        self.assertTrue(callable(EventStore.append))
        self.assertFalse(hasattr(bench_eventstore, "EventStore"))

    def test_bench_returns_json_keys(self):
        result = bench_eventstore.bench(20)
        self.assertIn("events", result)
        self.assertIn("append_sec", result)
        self.assertIn("replay_sec", result)
        self.assertIn("passed", result)
        self.assertEqual(result["events"], 20)


if __name__ == "__main__":
    unittest.main()

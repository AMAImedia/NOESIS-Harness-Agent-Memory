"""Tests for benchmarks.bench_projection (stdlib only, no repo writes)."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from benchmarks import bench_projection


class TestBenchProjection(unittest.TestCase):
    def test_digest_stability(self):
        result = bench_projection.bench(200)
        self.assertTrue(result["digest_stable"])
        self.assertEqual(result["events"], 200)
        self.assertGreaterEqual(result["seconds"], 0.0)

    def test_main_returns_zero(self):
        self.assertEqual(bench_projection.main(["--events", "50"]), 0)

    def test_no_repo_writes(self):
        root_files_before = set(os.listdir(ROOT))
        bench_projection.main(["--events", "30"])
        root_files_after = set(os.listdir(ROOT))
        self.assertEqual(root_files_before, root_files_after)

    def test_only_temp_side_effects(self):
        tmp_before = set(os.listdir(tempfile.gettempdir()))
        bench_projection.main(["--events", "40"])
        tmp_after = set(os.listdir(tempfile.gettempdir()))
        new_entries = tmp_after - tmp_before
        self.assertTrue(
            any(n.startswith("noesis_bench_projection_") for n in new_entries)
        )

    def test_lazy_import(self):
        self.assertFalse(hasattr(bench_projection, "pc"))
        pc = __import__("noesis_harness.projection_cache", fromlist=["x"])
        self.assertTrue(hasattr(pc, "project"))

    def test_default_events_arg(self):
        import noesis_harness.projection_cache as pc

        result = bench_projection.bench(25)
        self.assertEqual(bench_projection.main(["--events", "25"]), 0)
        scratch = tempfile.mkdtemp(prefix="noesis_tdp_")
        log_path = os.path.join(scratch, "events.jsonl")
        bench_projection._build_event_log(25, log_path)
        snapshot = pc.project(log_path)
        self.assertIsInstance(snapshot["digest"], str)
        self.assertTrue(snapshot["digest"].startswith("sha256:"))

    def test_projection_record_count_matches(self):
        result = bench_projection.bench(120)
        self.assertTrue(result["passed"])
        self.assertEqual(result["events"], 120)


if __name__ == "__main__":
    unittest.main()

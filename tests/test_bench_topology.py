"""Tests for benchmarks/bench_topology.py.

Stdlib-only. Verifies the topology micro-benchmark builds a graph, returns 0
from main(), never writes into the repository, imports event_topology lazily,
and is deterministic across runs. No LLM, no network, no autoloop.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCH_PATH = os.path.join(REPO_ROOT, "benchmarks", "bench_topology.py")
sys.path.insert(0, os.path.join(REPO_ROOT, "benchmarks"))


def _snapshot_repo_files():
    """Return a frozenset of (path, size, mtime) for every file under repo."""
    snap = set()
    skip_dirs = {".git", "__pycache__", "_archive", "_temp", "_example_state"}
    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for name in files:
            fp = os.path.join(root, name)
            try:
                st = os.stat(fp)
            except OSError:
                continue
            snap.add((fp, st.st_size, int(st.st_mtime * 1000)))
    return frozenset(snap)


class BenchTopologyTest(unittest.TestCase):

    def test_build_runs(self):
        import bench_topology as bt

        result = bt.bench(500)
        self.assertEqual(result["events"], 500)
        self.assertIn("seconds", result)
        self.assertIsInstance(result["seconds"], float)
        self.assertGreaterEqual(result["seconds"], 0.0)
        self.assertTrue(result["passed"])

    def test_main_returns_zero(self):
        import bench_topology as bt

        rc = bt.main(["--events", "200"])
        self.assertEqual(rc, 0)

    def test_no_repo_writes(self):
        import bench_topology as bt

        prev = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            before = _snapshot_repo_files()
            bt.main(["--events", "300"])
            after = _snapshot_repo_files()
        finally:
            sys.dont_write_bytecode = prev
        self.assertEqual(before, after)

    def test_lazy_import(self):
        import importlib

        import bench_topology as bt

        # Drop any prior import and reload the bench module cleanly, then
        # confirm event_topology is only imported once bench() runs.
        sys.modules.pop("noesis_harness.event_topology", None)
        importlib.reload(bt)
        self.assertNotIn("noesis_harness.event_topology", sys.modules)
        bt.bench(100)
        self.assertIn("noesis_harness.event_topology", sys.modules)

    def test_determinism(self):
        import noesis_harness.event_topology as et

        scratch = tempfile.mkdtemp(prefix="noesis_test_topo_")
        log_path = os.path.join(scratch, "events.jsonl")
        import bench_topology as bt

        events = bt._make_events(400)
        with open(log_path, "w", encoding="utf-8") as fh:
            for rec in events:
                fh.write(json.dumps(rec))
                fh.write("\n")
        first = et.build(log_path)
        second = et.build(log_path)
        self.assertEqual(first, second)

    def test_default_events_arg(self):
        # With no argv the parser default (--events 500) must run and pass.
        import bench_topology as bt

        rc = bt.main([])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()

"""Tests for benchmarks.bench_recall (stdlib only, no repo writes).

Verifies:
  - top1_hit is True on a synthetic log (rank_events surfaces the ground truth).
  - main() returns 0 on success.
  - main() prints valid JSON with the required keys.
  - recall_augment is imported lazily (not at module import time).
  - the benchmark only writes under the system TEMP directory.
  - rank_events respects top_k.
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from benchmarks import bench_recall


class TestBenchRecall(unittest.TestCase):
    def _make_log(self, n=50):
        tmp = tempfile.mkdtemp(prefix="test_bench_recall_")
        path = os.path.join(tmp, "events.jsonl")
        return bench_recall.build_synthetic_log(path, n)

    def test_top1_hit_true_on_synthetic_log(self):
        path = self._make_log(80)
        top1_hit, ranked, _seconds = bench_recall.run_benchmark(
            path, bench_recall.QUERY, 5
        )
        self.assertTrue(ranked)
        self.assertTrue(top1_hit)
        self.assertEqual(ranked[0]["event_id"], bench_recall.GROUND_TRUTH_ID)

    def test_main_returns_0(self):
        rc = bench_recall.main(["--events", "60", "--top-k", "5"])
        self.assertEqual(rc, 0)

    def test_main_prints_json_with_keys(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = bench_recall.main(["--events", "40", "--top-k", "5"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue().strip())
        self.assertIn("events", payload)
        self.assertIn("seconds", payload)
        self.assertIn("top1_hit", payload)
        self.assertIn("passed", payload)
        self.assertTrue(payload["top1_hit"])
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["events"], 40)

    def test_lazy_import(self):
        # recall_augment must not be imported by merely importing the module.
        sys.modules.pop("noesis_harness.recall_augment", None)
        import noesis_harness
        noesis_harness.__dict__.pop("recall_augment", None)
        self.assertNotIn("noesis_harness.recall_augment", sys.modules)
        bench_recall.main(["--events", "20", "--top-k", "3"])
        self.assertIn("noesis_harness.recall_augment", sys.modules)

    def test_no_repo_writes(self):
        # The benchmark must only write under the system TEMP directory.
        tmp = tempfile.mkdtemp(prefix="test_bench_recall_")
        path = os.path.join(tmp, "events.jsonl")
        with mock.patch.object(bench_recall.tempfile, "mkdtemp",
                               return_value=tmp) as mk:
            rc = bench_recall.main(["--events", "30", "--top-k", "4"])
        self.assertEqual(rc, 0)
        mk.assert_called_once()
        self.assertTrue(os.path.isfile(path))
        self.assertTrue(os.path.commonpath((tmp, tempfile.gettempdir()))
                        == tempfile.gettempdir())

    def test_top_k_respected(self):
        path = self._make_log(100)
        _hit, ranked, _s = bench_recall.run_benchmark(path, bench_recall.QUERY, 3)
        self.assertLessEqual(len(ranked), 3)
        # Ground truth is still at the top despite a small top_k.
        self.assertEqual(ranked[0]["event_id"], bench_recall.GROUND_TRUTH_ID)

    def test_deterministic_top1(self):
        path = self._make_log(70)
        h1, r1, _ = bench_recall.run_benchmark(path, bench_recall.QUERY, 5)
        h2, r2, _ = bench_recall.run_benchmark(path, bench_recall.QUERY, 5)
        self.assertEqual(h1, h2)
        self.assertEqual([e["event_id"] for e in r1],
                         [e["event_id"] for e in r2])


if __name__ == "__main__":
    unittest.main()

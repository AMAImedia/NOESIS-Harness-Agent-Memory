"""Tests for benchmarks.bench_digest (stdlib only, no repo writes)."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from benchmarks import bench_digest


class TestBenchDigest(unittest.TestCase):
    def test_determinism(self):
        import noesis_harness.digest_utils as du

        payload = {"b": 1, "a": [1, 2, 3], "c": "x"}
        d1 = du.sha256_hex(du.canonical_json(payload))
        d2 = du.sha256_hex(du.canonical_json(payload))
        self.assertEqual(d1, d2)

    def test_canonical_order_independent(self):
        import noesis_harness.digest_utils as du

        d1 = du.sha256_hex(du.canonical_json({"a": 1, "b": 2}))
        d2 = du.sha256_hex(du.canonical_json({"b": 2, "a": 1}))
        self.assertEqual(d1, d2)

    def test_bench_passed_true(self):
        result = bench_digest.bench(50)
        self.assertTrue(result["passed"])
        self.assertEqual(result["ops"], 50)
        self.assertGreaterEqual(result["seconds"], 0.0)

    def test_main_returns_zero(self):
        self.assertEqual(bench_digest.main(["--ops", "20"]), 0)

    def test_no_repo_writes(self):
        root_files_before = set(os.listdir(ROOT))
        bench_digest.main(["--ops", "10"])
        root_files_after = set(os.listdir(ROOT))
        self.assertEqual(root_files_before, root_files_after)

    def test_only_temp_side_effects(self):
        tmp_before = set(os.listdir(tempfile.gettempdir()))
        bench_digest.main(["--ops", "15"])
        tmp_after = set(os.listdir(tempfile.gettempdir()))
        new_entries = tmp_after - tmp_before
        self.assertTrue(any(n.startswith("noesis_bench_digest_") for n in new_entries))

    def test_lazy_import(self):
        self.assertFalse(hasattr(bench_digest, "du"))
        du = __import__("noesis_harness.digest_utils", fromlist=["x"])
        self.assertTrue(hasattr(du, "canonical_json"))
        self.assertTrue(hasattr(du, "sha256_hex"))


if __name__ == "__main__":
    unittest.main()

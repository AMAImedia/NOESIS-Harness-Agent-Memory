"""Tests for benchmarks/bench_merkle.py.

Stdlib-only. Verifies the merkle_chain benchmark returns sane timings, that
verify() is True after N appends, and that running the benchmark writes nothing
inside the repository (only to the system TEMP directory).
"""

from __future__ import annotations

import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import benchmarks.bench_merkle as bm  # noqa: E402


class TestBenchMerkle(unittest.TestCase):
    def _repo_tree(self):
        """Return a set of source files under the repo root (excluding .git
        and scratch/build dirs such as _temp, dist, _archive, .noesis_autoloop,
        __pycache__). Benchmarks write only to TEMP (which is _temp), so those
        scratch artifacts must not count as "writing into the repository"."""
        scratch = {"_temp", "dist", "_archive", ".noesis_autoloop", "__pycache__", "node_modules"}
        found = set()
        for root, dirs, files in os.walk(REPO_ROOT):
            dirs[:] = [d for d in dirs if d not in scratch and d != ".git"]
            for name in files:
                found.add(os.path.relpath(os.path.join(root, name), REPO_ROOT))
        return found

    def test_verify_true_after_n_appends(self):
        result = bm.bench(50)
        self.assertTrue(result["passed"])
        self.assertEqual(result["entries"], 50)

    def test_verify_true_after_large_n_appends(self):
        result = bm.bench(2000)
        self.assertTrue(result["passed"])

    def test_timings_present_and_positive(self):
        result = bm.bench(100)
        self.assertIn("append_sec", result)
        self.assertIn("verify_sec", result)
        self.assertGreaterEqual(result["append_sec"], 0.0)
        self.assertGreaterEqual(result["verify_sec"], 0.0)

    def test_main_returns_zero_when_passed(self):
        self.assertEqual(bm.main(["--entries", "100"]), 0)

    def test_main_returns_nonzero_if_not_passed(self):
        # Force a failure by passing a negative-ish impl via monkeypatching verify.
        import noesis_harness.merkle_chain as mc

        original = mc.HashChain.verify

        def _fail(self):
            return False

        mc.HashChain.verify = _fail
        try:
            self.assertNotEqual(bm.main(["--entries", "10"]), 0)
        finally:
            mc.HashChain.verify = original

    def test_no_repo_writes_on_main(self):
        before = self._repo_tree()
        rc = bm.main(["--entries", "200"])
        self.assertEqual(rc, 0)
        after = self._repo_tree()
        self.assertEqual(before, after)

    def test_no_repo_writes_on_bench(self):
        before = self._repo_tree()
        bm.bench(300)
        after = self._repo_tree()
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

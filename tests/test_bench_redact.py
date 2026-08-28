"""Tests for benchmarks.bench_redact (stdlib only, no repo writes).

Verifies:
  - emails are redacted by noesis_harness.redact.
  - main() returns 0 on success.
  - main() prints valid JSON with the required keys.
  - redact is imported lazily (not at module import time).
  - the benchmark does not write into the repository.
  - custom --lines is honoured.
"""

from __future__ import annotations

import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from benchmarks import bench_redact
from noesis_harness import redact


def _repo_snapshot():
    snap = set()
    for base, dirs, files in os.walk(ROOT):
        if ".git" in base or "__pycache__" in base or base.endswith("_archive"):
            continue
        for name in files:
            snap.add(os.path.join(base, name))
    return snap


class TestBenchRedact(unittest.TestCase):
    def test_emails_redacted(self):
        text = "contact alice@example.com about the file"
        out = redact.redact(text)
        self.assertNotIn("@", out)
        self.assertEqual(out, "contact [EMAIL] about the file")

    def test_phone_and_secret_redacted(self):
        out = redact.redact("call +1 555 123 4567 sk_lk2j3kl2j3lk2j3lk")
        self.assertIn("[PHONE]", out)
        self.assertIn("[SECRET]", out)

    def test_main_returns_zero(self):
        self.assertEqual(bench_redact.main([]), 0)

    def test_json_output_shape(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = bench_redact.main(["--lines", "15"])
        payload = json.loads(buf.getvalue().strip())
        self.assertEqual(rc, 0)
        self.assertEqual(payload["lines"], 15)
        self.assertIn("seconds", payload)
        self.assertIsInstance(payload["seconds"], float)
        self.assertTrue(payload["passed"])

    def test_custom_lines_honoured(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = bench_redact.main(["--lines", "9"])
        payload = json.loads(buf.getvalue().strip())
        self.assertEqual(rc, 0)
        self.assertEqual(payload["lines"], 9)

    def test_lazy_import(self):
        sys.modules.pop("noesis_harness.redact", None)
        sys.modules.pop("benchmarks.bench_redact", None)
        import benchmarks.bench_redact as fresh
        self.assertNotIn("noesis_harness.redact", sys.modules)
        self.assertTrue(hasattr(fresh, "main"))

    def test_no_repo_writes(self):
        before = _repo_snapshot()
        bench_redact.main(["--lines", "25"])
        after = _repo_snapshot()
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

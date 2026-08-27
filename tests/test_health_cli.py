"""Tests for noesis_harness/health_cli.py (read-only health CLI).

These tests confirm the CLI stays side-effect free, emits a stable JSON health
dict, exits 0 on a clean log, and degrades gracefully when an optional
projection module cannot be imported.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from typing import List

from noesis_harness import health_cli


def _write_events(path, events):
    # type: (str, List[dict]) -> None
    with open(path, "wb") as fh:
        for ev in events:
            fh.write((json.dumps(ev) + "\n").encode("utf-8"))


def _sample_events():
    # type: () -> List[dict]
    return [
        {"event_id": "e1", "type": "note", "seq": 1, "ts": 100,
         "payload": {"text": "a"}},
        {"event_id": "e2", "type": "note", "seq": 2, "ts": 200,
         "payload": {"text": "b"}},
        {"event_id": "e3", "type": "decision", "seq": 3, "ts": 300,
         "payload": {"text": "c"}},
    ]


def _sha256(path):
    # type: (str) -> str
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class HealthCliTest(unittest.TestCase):

    def setUp(self):
        # type: () -> None
        self.tmp = tempfile.mkdtemp(prefix="noesis_health_")
        self.events = os.path.join(self.tmp, "events.jsonl")
        _write_events(self.events, _sample_events())

    def tearDown(self):
        # type: () -> None
        for name in os.listdir(self.tmp):
            try:
                os.remove(os.path.join(self.tmp, name))
            except OSError:
                pass
        try:
            os.rmdir(self.tmp)
        except OSError:
            pass

    def test_json_shape(self):
        # The health dict always carries record_count, digests, audit_ok.
        rc = health_cli.main(["--events", self.events, "--json"])
        self.assertEqual(rc, 0)
        # Capture printed JSON by re-running with redirected stdout.
        import io
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            health_cli.main(["--events", self.events, "--json"])
        finally:
            sys.stdout = old
        data = json.loads(buf.getvalue())
        self.assertIn("record_count", data)
        self.assertIn("digests", data)
        self.assertIn("audit_ok", data)
        self.assertIn("missing", data)
        self.assertEqual(data["record_count"], 3)
        self.assertIn("metrics_snapshot", data["digests"])
        self.assertIn("summary_view", data["digests"])
        self.assertIn("self_audit", data["digests"])
        self.assertTrue(data["audit_ok"])

    def test_exit_zero_on_clean_log(self):
        rc = health_cli.main(["--events", self.events])
        self.assertEqual(rc, 0)

    def test_exit_zero_json_flag(self):
        rc = health_cli.main(["--events", self.events, "--json"])
        self.assertEqual(rc, 0)

    def test_read_only_guarantee(self):
        # The CLI must not alter the event log or create new files.
        before = _sha256(self.events)
        before_listing = set(os.listdir(self.tmp))
        rc = health_cli.main(["--events", self.events, "--json"])
        self.assertEqual(rc, 0)
        after = _sha256(self.events)
        after_listing = set(os.listdir(self.tmp))
        self.assertEqual(before, after, "event log bytes changed (not read-only)")
        self.assertEqual(before_listing, after_listing,
                         "CLI created or removed a file (not read-only)")

    def test_record_count_zero_on_empty(self):
        empty = os.path.join(self.tmp, "empty.jsonl")
        open(empty, "wb").close()
        import io
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            health_cli.main(["--events", empty, "--json"])
        finally:
            sys.stdout = old
        data = json.loads(buf.getvalue())
        self.assertEqual(data["record_count"], 0)
        self.assertTrue(data["audit_ok"])

    def _block_import(self, name):
        # type: (str) -> None
        """Make `from . import <name>` raise by clearing cache + attribute."""
        key = "noesis_harness." + name
        pkg = sys.modules.get("noesis_harness")
        if pkg is not None and hasattr(pkg, name):
            delattr(pkg, name)
        sys.modules[key] = None

    def _restore_import(self, name, sentinel):
        # type: (str, object) -> None
        key = "noesis_harness." + name
        if sentinel is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = sentinel

    def test_missing_dep_skip_path(self):
        # Force metrics_snapshot to be unimportable; main must skip it.
        sentinel = sys.modules.get("noesis_harness.metrics_snapshot")
        self._block_import("metrics_snapshot")
        try:
            import io
            buf = io.StringIO()
            old = sys.stdout
            sys.stdout = buf
            try:
                rc = health_cli.main(["--events", self.events, "--json"])
            finally:
                sys.stdout = old
            self.assertEqual(rc, 0)
            data = json.loads(buf.getvalue())
            self.assertIn("metrics_snapshot", data["missing"])
            # Remaining projections still resolve.
            self.assertNotIn("summary_view", data["missing"])
            self.assertNotIn("self_audit", data["missing"])
            self.assertTrue(data["audit_ok"])
        finally:
            self._restore_import("metrics_snapshot", sentinel)

    def test_all_deps_missing_still_exits_zero(self):
        sentinels = {}
        for name in ("metrics_snapshot", "summary_view", "self_audit"):
            key = "noesis_harness." + name
            sentinels[key] = sys.modules.get(key)
            self._block_import(name)
        try:
            import io
            buf = io.StringIO()
            old = sys.stdout
            sys.stdout = buf
            try:
                rc = health_cli.main(["--events", self.events, "--json"])
            finally:
                sys.stdout = old
            self.assertEqual(rc, 0)
            data = json.loads(buf.getvalue())
            self.assertEqual(set(data["missing"]),
                             {"metrics_snapshot", "summary_view", "self_audit"})
            self.assertTrue(data["audit_ok"])
        finally:
            for name in ("metrics_snapshot", "summary_view", "self_audit"):
                self._restore_import(name, sentinels["noesis_harness." + name])

    def test_audit_flags_failure(self):
        # A non-monotonic sequence should make self_audit report not ok.
        bad = os.path.join(self.tmp, "bad.jsonl")
        _write_events(bad, [
            {"event_id": "x1", "type": "note", "seq": 2, "payload": {}},
            {"event_id": "x2", "type": "note", "seq": 1, "payload": {}},
        ])
        rc = health_cli.main(["--events", bad, "--json"])
        self.assertEqual(rc, 1)
        import io
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            health_cli.main(["--events", bad, "--json"])
        finally:
            sys.stdout = old
        data = json.loads(buf.getvalue())
        self.assertFalse(data["audit_ok"])


if __name__ == "__main__":
    unittest.main()

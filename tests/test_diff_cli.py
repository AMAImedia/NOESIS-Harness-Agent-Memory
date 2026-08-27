"""tests/test_diff_cli.py

Tests for noesis_harness.diff_cli: read-only diffing of two projection
snapshots. Stdlib only; uses temp files and json to build fixtures.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from typing import Any, Dict

from noesis_harness import diff_cli


def _write_snapshot(entries: Dict[str, Any]) -> str:
    """Write a minimal snapshot JSON with the given by_key entries; return path."""
    snapshot: Dict[str, Any] = {
        "version": "1",
        "record_count": len(entries),
        "last_seq": None,
        "last_event_id": None,
        "types": {},
        "by_key": entries,
    }
    fd, path = tempfile.mkstemp(suffix=".json", prefix="snap_")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle)
    return path


def _cleanup(paths) -> None:
    for path in paths:
        try:
            os.remove(path)
        except OSError:
            pass


class DiffCliSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.paths = []

    def tearDown(self) -> None:
        _cleanup(self.paths)

    def _mk(self, entries: Dict[str, Any]) -> str:
        path = _write_snapshot(entries)
        self.paths.append(path)
        return path

    def test_added_detection(self) -> None:
        left = self._mk({"a": 1, "b": 2})
        right = self._mk({"a": 1, "b": 2, "c": 3})
        result = diff_cli.diff_snapshots(
            diff_cli.snapshot_file(left), diff_cli.snapshot_file(right)
        )
        self.assertEqual(result["added"], ["c"])
        self.assertEqual(result["removed"], [])
        self.assertEqual(result["changed"], [])

    def test_removed_detection(self) -> None:
        left = self._mk({"a": 1, "b": 2})
        right = self._mk({"a": 1})
        result = diff_cli.diff_snapshots(
            diff_cli.snapshot_file(left), diff_cli.snapshot_file(right)
        )
        self.assertEqual(result["added"], [])
        self.assertEqual(result["removed"], ["b"])
        self.assertEqual(result["changed"], [])

    def test_changed_detection(self) -> None:
        left = self._mk({"a": 1, "b": 2})
        right = self._mk({"a": 1, "b": 99})
        result = diff_cli.diff_snapshots(
            diff_cli.snapshot_file(left), diff_cli.snapshot_file(right)
        )
        self.assertEqual(result["added"], [])
        self.assertEqual(result["removed"], [])
        self.assertEqual(result["changed"], ["b"])

    def test_combined_added_removed_changed(self) -> None:
        left = self._mk({"a": 1, "b": 2, "c": 3})
        right = self._mk({"a": 1, "b": 20, "d": 4})
        result = diff_cli.diff_snapshots(
            diff_cli.snapshot_file(left), diff_cli.snapshot_file(right)
        )
        self.assertEqual(result["added"], ["d"])
        self.assertEqual(result["removed"], ["c"])
        self.assertEqual(result["changed"], ["b"])

    def test_identical_snapshots_no_diff(self) -> None:
        left = self._mk({"a": 1, "b": {"x": [1, 2]}})
        right = self._mk({"a": 1, "b": {"x": [1, 2]}})
        result = diff_cli.diff_snapshots(
            diff_cli.snapshot_file(left), diff_cli.snapshot_file(right)
        )
        self.assertEqual(result["added"], [])
        self.assertEqual(result["removed"], [])
        self.assertEqual(result["changed"], [])

    def test_missing_left_file_returns_exit_2(self) -> None:
        existing = self._mk({"a": 1})
        code = diff_cli.main(["--left", "no_such_file.json", "--right", existing])
        self.assertEqual(code, 2)

    def test_missing_right_file_returns_exit_2(self) -> None:
        existing = self._mk({"a": 1})
        code = diff_cli.main(["--right", "no_such_file.json", "--left", existing])
        self.assertEqual(code, 2)

    def test_main_exit_0_with_differences(self) -> None:
        left = self._mk({"a": 1})
        right = self._mk({"a": 2})
        code = diff_cli.main(["--left", left, "--right", right])
        self.assertEqual(code, 0)

    def test_deterministic_output(self) -> None:
        left = self._mk({"z": 1, "a": 2, "m": 3})
        right = self._mk({"z": 1, "a": 9, "n": 4})
        r1 = diff_cli.diff_snapshots(
            diff_cli.snapshot_file(left), diff_cli.snapshot_file(right)
        )
        r2 = diff_cli.diff_snapshots(
            diff_cli.snapshot_file(left), diff_cli.snapshot_file(right)
        )
        self.assertEqual(r1, r2)
        self.assertEqual(r1["added"], sorted(r1["added"]))
        self.assertEqual(r1["removed"], sorted(r1["removed"]))
        self.assertEqual(r1["changed"], sorted(r1["changed"]))

    def test_json_output_flag(self) -> None:
        left = self._mk({"a": 1})
        right = self._mk({"b": 2})
        code = diff_cli.main(["--left", left, "--right", right, "--json"])
        self.assertEqual(code, 0)

    def test_structural_equality_not_identity(self) -> None:
        left = self._mk({"a": {"x": 1, "y": 2}})
        right = self._mk({"a": {"y": 2, "x": 1}})
        result = diff_cli.diff_snapshots(
            diff_cli.snapshot_file(left), diff_cli.snapshot_file(right)
        )
        self.assertEqual(result["changed"], [])


if __name__ == "__main__":
    unittest.main()

"""Tests for noesis_harness.atomic_write."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

from noesis_harness.atomic_write import (
    AtomicWriteError,
    atomic_append_line,
    atomic_write_bytes,
    atomic_write_text,
    prune_temp_files,
    read_text,
    unique_temp_name,
)


class TestAtomicWrite(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = self._tmp.name
        self.path = os.path.join(self.dir, "target.txt")

    def _tmp_siblings(self):
        return sorted(
            name
            for name in os.listdir(self.dir)
            if ".tmp-" in name
            and os.path.isfile(os.path.join(self.dir, name))
        )

    def test_write_then_read_roundtrip(self):
        atomic_write_text(self.path, "hello world")
        self.assertEqual(read_text(self.path), "hello world")

    def test_write_returns_final_path(self):
        result = atomic_write_text(self.path, "x")
        self.assertEqual(result, self.path)

    def test_write_bytes_roundtrip(self):
        atomic_write_bytes(self.path, b"\x00\x01\x02")
        with open(self.path, "rb") as handle:
            self.assertEqual(handle.read(), b"\x00\x01\x02")

    def test_overwrite_existing_preserves_content_on_success(self):
        atomic_write_text(self.path, "first")
        atomic_write_text(self.path, "second")
        self.assertEqual(read_text(self.path), "second")

    def test_unique_temp_names_differ(self):
        names = {unique_temp_name(self.path) for _ in range(20)}
        self.assertEqual(len(names), 20)

    def test_temp_name_never_escapes_directory(self):
        nested = os.path.join(self.dir, "a", "b", "file.bin")
        temp = unique_temp_name(nested)
        self.assertEqual(os.path.dirname(temp), os.path.dirname(nested))

    def test_temp_name_shape(self):
        temp = unique_temp_name(self.path)
        base = os.path.basename(temp)
        self.assertTrue(base.startswith("target.txt.tmp-"))
        suffix = base[len("target.txt.tmp-"):]
        pid_part, _, rand_part = suffix.partition("-")
        self.assertEqual(pid_part, str(os.getpid()))
        self.assertEqual(len(rand_part), 8)

    def test_failed_replace_leaves_original_intact(self):
        atomic_write_text(self.path, "original")
        with mock.patch(
            "noesis_harness.atomic_write.os.replace",
            side_effect=PermissionError("locked"),
        ):
            with self.assertRaises(AtomicWriteError):
                atomic_write_text(self.path, "replacement", retries=2)
        self.assertEqual(read_text(self.path), "original")

    def test_failed_replace_removes_temp(self):
        atomic_write_text(self.path, "original")
        with mock.patch(
            "noesis_harness.atomic_write.os.replace",
            side_effect=PermissionError("locked"),
        ):
            with self.assertRaises(AtomicWriteError):
                atomic_write_text(self.path, "replacement", retries=1)
        self.assertEqual(self._tmp_siblings(), [])

    def test_failed_write_leaves_no_target_when_absent(self):
        missing = os.path.join(self.dir, "brand-new.txt")
        with mock.patch(
            "noesis_harness.atomic_write.os.replace",
            side_effect=PermissionError("locked"),
        ):
            with self.assertRaises(AtomicWriteError):
                atomic_write_text(missing, "data", retries=1)
        self.assertFalse(os.path.exists(missing))

    def test_parent_dirs_created(self):
        nested = os.path.join(self.dir, "x", "y", "z", "deep.txt")
        atomic_write_text(nested, "deep")
        self.assertEqual(read_text(nested), "deep")

    def test_append_line_accumulates(self):
        atomic_append_line(self.path, "one")
        atomic_append_line(self.path, "two")
        atomic_append_line(self.path, "three")
        self.assertEqual(read_text(self.path), "one\ntwo\nthree\n")

    def test_append_line_single_call_no_extra_newline(self):
        atomic_append_line(self.path, "already\n")
        atomic_append_line(self.path, "next")
        self.assertEqual(read_text(self.path), "already\nnext\n")

    def test_append_does_not_use_temp(self):
        atomic_append_line(self.path, "line")
        self.assertEqual(self._tmp_siblings(), [])

    def test_read_text_missing_returns_none(self):
        self.assertIsNone(read_text(os.path.join(self.dir, "nope.txt")))

    def test_prune_removes_only_tmp_files(self):
        target = os.path.join(self.dir, "keep.txt")
        with open(target, "w", encoding="utf-8") as handle:
            handle.write("keep")
        with open(os.path.join(self.dir, "other.tmp"), "w") as handle:
            handle.write("not ours")
        with open(os.path.join(self.dir, "a.tmp-1"), "w") as handle:
            handle.write("temp a")
        with open(os.path.join(self.dir, "b.tmp-2"), "w") as handle:
            handle.write("temp b")
        os.mkdir(os.path.join(self.dir, "c.tmp-3"))

        removed = prune_temp_files(self.dir)

        self.assertEqual(removed, ["a.tmp-1", "b.tmp-2"])
        self.assertTrue(os.path.exists(target))
        self.assertTrue(os.path.exists(os.path.join(self.dir, "other.tmp")))
        self.assertTrue(os.path.isdir(os.path.join(self.dir, "c.tmp-3")))

    def test_prune_returns_sorted_names(self):
        for name in ("z.tmp-1", "a.tmp-2", "m.tmp-3"):
            with open(os.path.join(self.dir, name), "w") as handle:
                handle.write("x")
        removed = prune_temp_files(self.dir)
        self.assertEqual(removed, sorted(removed))

    def test_prune_keep_newest(self):
        names = ["old.tmp-1", "mid.tmp-2", "new.tmp-3"]
        for index, name in enumerate(names):
            full = os.path.join(self.dir, name)
            with open(full, "w") as handle:
                handle.write("x")
            os.utime(full, (1000 + index, 1000 + index))
        removed = prune_temp_files(self.dir, keep=1)
        self.assertEqual(removed, ["mid.tmp-2", "old.tmp-1"])
        self.assertTrue(os.path.exists(os.path.join(self.dir, "new.tmp-3")))

    def test_prune_missing_directory(self):
        self.assertEqual(prune_temp_files(os.path.join(self.dir, "absent")), [])

    def test_unicode_roundtrip(self):
        text = "cafe \u0301 \u4e2d\u6587 \u0440\u0443\u0441\u0441\u043a\u0438\u0439 \U0001F600"
        atomic_write_text(self.path, text)
        self.assertEqual(read_text(self.path), text)

    def test_unicode_custom_encoding(self):
        text = "\u041f\u0440\u0438\u0432\u0435\u0442"
        atomic_write_text(self.path, text, encoding="utf-16")
        self.assertEqual(read_text(self.path, encoding="utf-16"), text)

    def test_no_leftover_temp_after_successful_write(self):
        atomic_write_text(self.path, "done")
        self.assertEqual(self._tmp_siblings(), [])
        self.assertEqual(sorted(os.listdir(self.dir)), ["target.txt"])

    def test_atomic_write_error_is_runtime_error(self):
        self.assertTrue(issubclass(AtomicWriteError, RuntimeError))

    def test_write_bytes_rejects_non_bytes(self):
        with self.assertRaises(TypeError):
            atomic_write_bytes(self.path, "not bytes")

    def test_write_text_rejects_non_str(self):
        with self.assertRaises(TypeError):
            atomic_write_text(self.path, b"bytes")


if __name__ == "__main__":
    unittest.main()

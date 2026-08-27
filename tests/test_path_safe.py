"""Tests for noesis_harness.path_safe.

Covers normal joins, traversal rejection, absolute-escape rejection,
symlink-ish string rejection, determinism, and unicode handling. Stdlib only.
"""

import os
import unittest

from noesis_harness import path_safe


class TestJoinUnderNormal(unittest.TestCase):

    def test_simple_join(self):
        out = path_safe.join_under("/data/root", "a", "b.txt")
        self.assertTrue(path_safe.is_safe_under("/data/root", out))
        self.assertTrue(str(out).endswith(os.path.join("a", "b.txt")))

    def test_single_part(self):
        out = path_safe.join_under("/base", "file.log")
        self.assertTrue(str(out).endswith("file.log"))
        self.assertTrue(path_safe.is_safe_under("/base", out))

    def test_empty_parts(self):
        out = path_safe.join_under("/base")
        self.assertTrue(path_safe.is_safe_under("/base", out))

    def test_returned_path_is_under_base(self):
        out = path_safe.join_under("/base", "x", "y", "z")
        self.assertTrue(path_safe.is_safe_under("/base", out))


class TestJoinUnderRejections(unittest.TestCase):

    def test_traversal_rejected(self):
        with self.assertRaises(ValueError):
            path_safe.join_under("/base", "..", "etc")

    def test_nested_traversal_rejected(self):
        with self.assertRaises(ValueError):
            path_safe.join_under("/base", "a", "..", "..", "secret")

    def test_absolute_part_rejected(self):
        with self.assertRaises(ValueError):
            path_safe.join_under("/base", "/etc/passwd")

    def test_drive_relative_rejected(self):
        with self.assertRaises(ValueError):
            path_safe.join_under("/base", "c:windows")

    def test_symlink_ish_string_rejected(self):
        # A string that merely names a component "link" is fine, but a
        # symlink-style escape target ("link/../../out") must be rejected.
        with self.assertRaises(ValueError):
            path_safe.join_under("/base", "link", "..", "..", "escape")

    def test_traversal_after_join_rejected(self):
        with self.assertRaises(ValueError):
            path_safe.join_under("/base", "a/../../outside")


class TestIsSafeUnder(unittest.TestCase):

    def test_under_true(self):
        self.assertTrue(path_safe.is_safe_under("/base", "/base/sub/x"))

    def test_outside_false(self):
        self.assertFalse(path_safe.is_safe_under("/base", "/other/x"))

    def test_base_itself_true(self):
        self.assertTrue(path_safe.is_safe_under("/base", "/base"))

    def test_sibling_prefix_false(self):
        # /baseball must not be considered under /base.
        self.assertFalse(path_safe.is_safe_under("/base", "/baseball/x"))


class TestDeterminism(unittest.TestCase):

    def test_deterministic_join(self):
        a = path_safe.join_under("/base", "a", "b", "c")
        b = path_safe.join_under("/base", "a", "b", "c")
        self.assertEqual(a, b)

    def test_deterministic_is_safe(self):
        self.assertEqual(
            path_safe.is_safe_under("/base", "/base/x"),
            path_safe.is_safe_under("/base", "/base/x"),
        )


class TestUnicode(unittest.TestCase):

    def test_unicode_parts(self):
        out = path_safe.join_under("/base", "café", "файл.txt")
        self.assertTrue(path_safe.is_safe_under("/base", out))

    def test_unicode_base(self):
        out = path_safe.join_under("/böse", "x")
        self.assertTrue(path_safe.is_safe_under("/böse", out))


if __name__ == "__main__":
    unittest.main()

"""tests/test_version.py

Unit tests for noesis_harness.version. Pure, stdlib-only, no writes.
"""

import os
import unittest

from noesis_harness import version as v


class TestVersionTuple(unittest.TestCase):
    def test_shape_is_tuple_of_ints(self):
        t = v.version_tuple()
        self.assertIsInstance(t, tuple)
        self.assertGreaterEqual(len(t), 3)
        for part in t:
            self.assertIsInstance(part, int)

    def test_known_version_from_source(self):
        # pyproject.toml in this repo is "0.5.0"; tuple must be (0, 5, 0).
        self.assertEqual(v.version_tuple(), (0, 5, 0))

    def test_version_string_matches_tuple(self):
        s = v.get_version_string()
        self.assertIsInstance(s, str)
        self.assertTrue(s.strip())


class TestIdentity(unittest.TestCase):
    def test_determinism_repeatable(self):
        a = v.agent_identity("alpha")
        b = v.agent_identity("alpha")
        self.assertEqual(a, b)

    def test_different_names_differ(self):
        self.assertNotEqual(v.agent_identity("alpha"), v.agent_identity("beta"))

    def test_hex_digest_format(self):
        ident = v.agent_identity("alpha")
        self.assertEqual(len(ident), 64)
        int(ident, 16)  # must be valid hex

    def test_name_bound_to_version(self):
        # Identity must change if the effective version string changes.
        base = v.agent_identity("alpha")
        original = v.get_version_string

        def fake_v1():
            return "9.9.9"

        try:
            v.get_version_string = fake_v1
            self.assertNotEqual(base, v.agent_identity("alpha"))
        finally:
            v.get_version_string = original


class TestMissingPyproject(unittest.TestCase):
    def test_fallback_when_pyproject_unreadable(self):
        # Point at a non-existent path; getter must fall back to VERSION.
        original = v._PYPROJECT_PATH
        try:
            v._PYPROJECT_PATH = os.path.join(original, "does_not_exist.toml")
            self.assertEqual(v.get_version_string(), v.VERSION)
            self.assertEqual(v.version_tuple(), v.version_tuple())
        finally:
            v._PYPROJECT_PATH = original


class TestNoWrites(unittest.TestCase):
    def test_read_only_does_not_create_file(self):
        # Calling public APIs must not create or modify any state file.
        before = os.path.exists(v._PYPROJECT_PATH)
        v.version_tuple()
        v.agent_identity("gamma")
        self.assertEqual(os.path.exists(v._PYPROJECT_PATH), before)


if __name__ == "__main__":
    unittest.main()

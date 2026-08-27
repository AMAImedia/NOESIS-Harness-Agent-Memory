"""Tests for noesis_harness.capability_view.

Covers manifest loading, the enabled filter, digest stability/determinism,
empty manifests, and missing-file handling. A temp manifest JSON is created
in this test directory (no commit, no external deps).
"""

import json
import os
import tempfile
import unittest

from noesis_harness import capability_view


class CapabilityViewTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="capview_")
        self.manifest_path = os.path.join(self.tmp, "capabilities.json")

    def _write(self, obj):
        with open(self.manifest_path, "w", encoding="utf-8") as handle:
            json.dump(obj, handle)

    def test_missing_file_raises(self):
        missing = os.path.join(self.tmp, "does_not_exist.json")
        with self.assertRaises(OSError):
            capability_view.view(missing)

    def test_basic_view_shape(self):
        self._write({
            "capabilities": [
                {"name": "read", "enabled": True},
                {"name": "write", "enabled": False},
            ]
        })
        v = capability_view.view(self.manifest_path)
        self.assertEqual(v["count"], 2)
        self.assertEqual(v["enabled_count"], 1)
        self.assertEqual(v["path"], self.manifest_path)
        self.assertEqual(len(v["digest"]), 64)

    def test_filter_enabled(self):
        self._write({
            "capabilities": [
                {"name": "read", "enabled": True},
                {"name": "write", "enabled": False},
                {"name": "exec", "enabled": True},
            ]
        })
        v = capability_view.view(self.manifest_path)
        enabled = capability_view.filter_enabled(v)
        self.assertEqual(enabled, ["exec", "read"])

    def test_filter_enabled_empty(self):
        self._write({"capabilities": [{"name": "x", "enabled": False}]})
        v = capability_view.view(self.manifest_path)
        self.assertEqual(capability_view.filter_enabled(v), [])

    def test_digest_stability(self):
        self._write({
            "capabilities": [
                {"name": "a", "enabled": True},
                {"name": "b", "enabled": False},
            ]
        })
        d1 = capability_view.view(self.manifest_path)["digest"]
        d2 = capability_view.view(self.manifest_path)["digest"]
        self.assertEqual(d1, d2)

    def test_digest_order_independent(self):
        forward = {"capabilities": [
            {"name": "a", "enabled": True},
            {"name": "b", "enabled": False},
        ]}
        backward = {"capabilities": [
            {"name": "b", "enabled": False},
            {"name": "a", "enabled": True},
        ]}
        p1 = os.path.join(self.tmp, "fwd.json")
        p2 = os.path.join(self.tmp, "bwd.json")
        for path, obj in ((p1, forward), (p2, backward)):
            with open(path, "w", encoding="utf-8") as h:
                json.dump(obj, h)
        self.assertEqual(
            capability_view.view(p1)["digest"],
            capability_view.view(p2)["digest"],
        )

    def test_empty_manifest(self):
        self._write({"capabilities": []})
        v = capability_view.view(self.manifest_path)
        self.assertEqual(v["count"], 0)
        self.assertEqual(v["enabled_count"], 0)
        self.assertEqual(capability_view.filter_enabled(v), [])
        self.assertEqual(len(v["digest"]), 64)

    def test_bare_list_manifest(self):
        self._write([
            {"name": "alpha", "enabled": True},
            "beta",
        ])
        v = capability_view.view(self.manifest_path)
        self.assertEqual(v["count"], 2)
        self.assertEqual(v["enabled_count"], 2)
        self.assertEqual(capability_view.filter_enabled(v), ["alpha", "beta"])

    def test_default_enabled_is_true(self):
        self._write([{"name": "only"}])
        v = capability_view.view(self.manifest_path)
        self.assertTrue(v["capabilities"][0]["enabled"])

    def test_enabled_flag_change_changes_digest(self):
        base = {"capabilities": [{"name": "a", "enabled": True}]}
        flipped = {"capabilities": [{"name": "a", "enabled": False}]}
        p1 = os.path.join(self.tmp, "on.json")
        p2 = os.path.join(self.tmp, "off.json")
        for path, obj in ((p1, base), (p2, flipped)):
            with open(path, "w", encoding="utf-8") as h:
                json.dump(obj, h)
        self.assertNotEqual(
            capability_view.view(p1)["digest"],
            capability_view.view(p2)["digest"],
        )

    def test_determinism_across_instances(self):
        self._write({
            "capabilities": [
                {"name": "x", "enabled": False},
                {"name": "y", "enabled": True},
                {"name": "z", "enabled": True},
            ]
        })
        a = capability_view.view(self.manifest_path)
        b = capability_view.view(self.manifest_path)
        self.assertEqual(a, b)
        self.assertEqual(
            capability_view.filter_enabled(a),
            capability_view.filter_enabled(b),
        )


if __name__ == "__main__":
    unittest.main()

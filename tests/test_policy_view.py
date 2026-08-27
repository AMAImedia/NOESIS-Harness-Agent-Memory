"""Tests for noesis_harness.policy_view.

Covers: missing file, malformed file, enabled filtering, digest stability,
empty policy, determinism, order-independence of digest, rule sorting, and
metadata-independence of the digest.
"""

import json
import os
import tempfile
import unittest

from noesis_harness import policy_view


def _write_policy(payload):
    handle, path = tempfile.mkstemp(suffix=".json", prefix="policy_test_")
    with os.fdopen(handle, "w", encoding="utf-8") as fp:
        json.dump(payload, fp)
    return path


class PolicyViewTest(unittest.TestCase):

    def _write(self, payload):
        handle, path = tempfile.mkstemp(suffix=".json", prefix="policy_test_")
        with os.fdopen(handle, "w", encoding="utf-8") as fp:
            json.dump(payload, fp)
        self.addCleanup(os.remove, path)
        return path

    def test_missing_file_raises(self):
        with self.assertRaises(OSError):
            policy_view.view("/nonexistent/path/policy_abc123.json")

    def test_malformed_json_raises(self):
        handle, path = tempfile.mkstemp(suffix=".json", prefix="policy_test_")
        with os.fdopen(handle, "w", encoding="utf-8") as fp:
            fp.write("{ not valid json ")
        self.addCleanup(os.remove, path)
        with self.assertRaises(ValueError):
            policy_view.view(path)

    def test_basic_view_shape(self):
        path = self._write({
            "rules": [
                {"id": "allow_read", "enabled": True},
                {"id": "deny_write", "enabled": False},
            ]
        })
        v = policy_view.view(path)
        self.assertEqual(v["count"], 2)
        self.assertEqual(v["enabled_count"], 1)
        self.assertEqual(v["path"], path)
        self.assertEqual(len(v["digest"]), 64)

    def test_filter_enabled_returns_only_enabled_ids(self):
        path = self._write({
            "rules": [
                {"id": "a", "enabled": True},
                {"id": "b", "enabled": False},
                {"id": "c", "enabled": True},
            ]
        })
        v = policy_view.view(path)
        self.assertEqual(policy_view.filter_enabled(v), ["a", "c"])

    def test_filter_enabled_empty_when_all_disabled(self):
        path = self._write({
            "rules": [
                {"id": "x", "enabled": False},
                {"id": "y", "enabled": False},
            ]
        })
        v = policy_view.view(path)
        self.assertEqual(policy_view.filter_enabled(v), [])
        self.assertEqual(v["enabled_count"], 0)

    def test_empty_policy(self):
        path = self._write({"rules": []})
        v = policy_view.view(path)
        self.assertEqual(v["count"], 0)
        self.assertEqual(v["enabled_count"], 0)
        self.assertEqual(v["rules"], [])
        self.assertEqual(policy_view.filter_enabled(v), [])
        self.assertEqual(
            v["digest"],
            policy_view.view(self._write({"rules": []}))["digest"],
        )

    def test_digest_stability(self):
        path = self._write({
            "rules": [
                {"id": "a", "enabled": True},
                {"id": "b", "enabled": False},
            ]
        })
        self.assertEqual(
            policy_view.view(path)["digest"],
            policy_view.view(path)["digest"],
        )

    def test_determinism_across_files(self):
        p1 = self._write({
            "rules": [
                {"id": "a", "enabled": True},
                {"id": "b", "enabled": False},
            ]
        })
        p2 = self._write({
            "rules": [
                {"id": "a", "enabled": True},
                {"id": "b", "enabled": False},
            ]
        })
        self.assertEqual(
            policy_view.view(p1)["digest"],
            policy_view.view(p2)["digest"],
        )

    def test_order_independence_of_digest(self):
        p1 = self._write({
            "rules": [
                {"id": "a", "enabled": True},
                {"id": "b", "enabled": False},
                {"id": "c", "enabled": True},
            ]
        })
        p2 = self._write({
            "rules": [
                {"id": "c", "enabled": True},
                {"id": "a", "enabled": True},
                {"id": "b", "enabled": False},
            ]
        })
        self.assertEqual(
            policy_view.view(p1)["digest"],
            policy_view.view(p2)["digest"],
        )

    def test_rules_sorted_by_id(self):
        path = self._write({
            "rules": [
                {"id": "zebra", "enabled": True},
                {"id": "alpha", "enabled": True},
                {"id": "mango", "enabled": True},
            ]
        })
        v = policy_view.view(path)
        ids = [rule["id"] for rule in v["rules"]]
        self.assertEqual(ids, ["alpha", "mango", "zebra"])

    def test_digest_ignores_extra_metadata(self):
        p1 = self._write({
            "rules": [
                {"id": "a", "enabled": True, "note": "first", "weight": 3},
                {"id": "b", "enabled": False, "note": "second"},
            ]
        })
        p2 = self._write({
            "rules": [
                {"id": "b", "enabled": False, "note": "changed", "weight": 99},
                {"id": "a", "enabled": True, "note": "first", "weight": 3},
            ]
        })
        self.assertEqual(
            policy_view.view(p1)["digest"],
            policy_view.view(p2)["digest"],
        )

    def test_raw_rule_preserved(self):
        path = self._write({
            "rules": [
                {"id": "a", "enabled": True, "scope": "read"},
            ]
        })
        v = policy_view.view(path)
        self.assertEqual(v["rules"][0]["raw"].get("scope"), "read")

    def test_bare_list_policy(self):
        path = self._write([
            {"id": "a", "enabled": True},
            {"id": "b", "enabled": False},
        ])
        v = policy_view.view(path)
        self.assertEqual(v["count"], 2)
        self.assertEqual(policy_view.filter_enabled(v), ["a"])

    def test_missing_id_raises(self):
        path = self._write({"rules": [{"enabled": True}]})
        with self.assertRaises(ValueError):
            policy_view.view(path)

    def test_non_object_rule_raises(self):
        path = self._write({"rules": ["not-an-object"]})
        with self.assertRaises(ValueError):
            policy_view.view(path)

    def test_non_list_rules_raises(self):
        path = self._write({"rules": {"a": True}})
        with self.assertRaises(ValueError):
            policy_view.view(path)


if __name__ == "__main__":
    unittest.main()

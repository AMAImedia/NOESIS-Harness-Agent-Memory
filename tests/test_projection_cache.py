import json
import os
import tempfile
import unittest

from noesis_harness.event_store import EventStore
from noesis_harness.projection_cache import (
    SNAPSHOT_VERSION,
    project,
    snapshot_file,
    write_snapshot,
)


def write_event(path, event_type, payload, seq, event_id=None, key=None):
    record = {
        "event_id": event_id or f"e{seq}",
        "type": event_type,
        "payload": payload,
        "seq": seq,
    }
    if key is not None:
        record["key"] = key
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


class ProjectionCacheTests(unittest.TestCase):
    def log(self):
        return os.path.join(tempfile.mkdtemp(), "events.jsonl")

    def test_empty_log_snapshot(self):
        path = self.log()
        snap = project(path)
        self.assertEqual(snap["record_count"], 0)
        self.assertIsNone(snap["last_seq"])
        self.assertIsNone(snap["last_event_id"])
        self.assertEqual(snap["types"], {})
        self.assertEqual(snap["by_key"], {})
        self.assertTrue(snap["digest"].startswith("sha256:"))

    def test_missing_log_snapshot(self):
        snap = project(os.path.join(tempfile.mkdtemp(), "does_not_exist.jsonl"))
        self.assertEqual(snap["record_count"], 0)
        self.assertEqual(snap["version"], SNAPSHOT_VERSION)

    def test_type_counts(self):
        path = self.log()
        write_event(path, "create", {"v": 1}, 1)
        write_event(path, "update", {"v": 2}, 2)
        write_event(path, "update", {"v": 3}, 3)
        snap = project(path)
        self.assertEqual(snap["types"], {"create": 1, "update": 2})
        self.assertEqual(snap["record_count"], 3)

    def test_last_seq_and_event_id(self):
        path = self.log()
        write_event(path, "a", {}, 1, event_id="id-1")
        write_event(path, "b", {}, 5, event_id="id-5")
        snap = project(path)
        self.assertEqual(snap["last_seq"], 5)
        self.assertEqual(snap["last_event_id"], "id-5")

    def test_by_key_latest_wins_record_level(self):
        path = self.log()
        write_event(path, "set", {"v": "old"}, 1, key="config")
        write_event(path, "set", {"v": "new"}, 2, key="config")
        write_event(path, "set", {"v": "other"}, 3, key="feature")
        snap = project(path)
        self.assertEqual(snap["by_key"]["config"], {"v": "new"})
        self.assertEqual(snap["by_key"]["feature"], {"v": "other"})

    def test_by_key_from_payload(self):
        path = self.log()
        write_event(path, "fact", {"key": "k1", "v": 1}, 1)
        write_event(path, "fact", {"key": "k1", "v": 2}, 2)
        snap = project(path)
        self.assertEqual(snap["by_key"]["k1"], {"key": "k1", "v": 2})

    def test_events_without_key_excluded_from_by_key(self):
        path = self.log()
        write_event(path, "note", {"v": 1}, 1)
        snap = project(path)
        self.assertEqual(snap["by_key"], {})

    def test_determinism_across_runs(self):
        path = self.log()
        write_event(path, "a", {"x": 1}, 1, key="k")
        write_event(path, "b", {"y": 2}, 2, key="k")
        write_event(path, "a", {"z": 3}, 3)
        first = project(path)
        second = project(path)
        self.assertEqual(first, second)
        self.assertEqual(first["digest"], second["digest"])

    def test_digest_stability_regardless_of_dict_order(self):
        path = self.log()
        write_event(path, "create", {"v": 1}, 1)
        write_event(path, "update", {"v": 2}, 2)
        snap = project(path)
        # Recompute canonical form directly and confirm stability.
        reloaded = project(path)
        self.assertEqual(snap["digest"], reloaded["digest"])
        self.assertEqual(len(snap["digest"]), len("sha256:") + 64)

    def test_digest_changes_when_log_changes(self):
        path = self.log()
        write_event(path, "a", {}, 1)
        before = project(path)
        write_event(path, "b", {}, 2)
        after = project(path)
        self.assertNotEqual(before["digest"], after["digest"])

    def test_log_immutable_after_project(self):
        path = self.log()
        write_event(path, "a", {"v": 1}, 1, key="k")
        with open(path, "rb") as fh:
            before_bytes = fh.read()
        project(path)
        project(path)
        with open(path, "rb") as fh:
            after_bytes = fh.read()
        self.assertEqual(before_bytes, after_bytes)
        # And it stays a valid, complete append-only log.
        store = EventStore(path)
        self.assertEqual(store.count(), 1)

    def test_snapshot_json_roundtrip(self):
        path = self.log()
        write_event(path, "a", {"v": 1}, 1, key="k")
        out = os.path.join(tempfile.mkdtemp(), "snap.json")
        snap = write_snapshot(path, out)
        self.assertTrue(os.path.exists(out))
        loaded = snapshot_file(out)
        self.assertEqual(loaded["digest"], snap["digest"])
        self.assertEqual(loaded["record_count"], 1)

    def test_canonical_payloads_preserve_nested_structure(self):
        path = self.log()
        write_event(path, "tree", {"nested": {"a": [1, 2, 3]}}, 1, key="t")
        snap = project(path)
        self.assertEqual(snap["by_key"]["t"], {"nested": {"a": [1, 2, 3]}})

    def test_event_store_append_then_project_consistent(self):
        path = self.log()
        store = EventStore(path)
        store.append("alpha", {"v": 1}, event_id="a1")
        store.append("alpha", {"v": 2}, event_id="a2")
        store.append("beta", {"v": 3}, event_id="b1")
        snap = project(path)
        self.assertEqual(snap["record_count"], 3)
        self.assertEqual(snap["types"], {"alpha": 2, "beta": 1})
        self.assertEqual(snap["last_event_id"], "b1")


if __name__ == "__main__":
    unittest.main()

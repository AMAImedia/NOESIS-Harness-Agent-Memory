"""Tests for noesis_harness/event_topology.py

Stdlib only. Exercises: empty log, isolated nodes, chain, diamond,
fork/join, self-loop (cycle) detection, larger cycle detection, missing file,
malformed-line resilience, determinism, and read-only (source unchanged).
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from noesis_harness import event_topology


def _write_log(path, records):
    with open(path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")


class EventTopologyTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "events.jsonl")

    def _event(self, eid, payload=None):
        return {"event_id": eid, "type": "t", "payload": payload or {}, "seq": 0}

    def test_empty_log(self):
        _write_log(self.path, [])
        topo = event_topology.build(self.path)
        self.assertEqual(topo["nodes"], [])
        self.assertEqual(topo["edges"], [])
        self.assertEqual(topo["roots"], [])
        self.assertEqual(topo["leaves"], [])
        self.assertTrue(topo["cycle_free"])

    def test_isolated_nodes(self):
        _write_log(self.path, [self._event("a"), self._event("b")])
        topo = event_topology.build(self.path)
        self.assertEqual(topo["nodes"], ["a", "b"])
        self.assertEqual(topo["edges"], [])
        # every node is both a root (no deps) and a leaf (no dependents)
        self.assertEqual(topo["roots"], ["a", "b"])
        self.assertEqual(topo["leaves"], ["a", "b"])

    def test_chain(self):
        _write_log(self.path, [
            self._event("a"),
            self._event("b", {"parent": "a"}),
            self._event("c", {"parent": "b"}),
        ])
        topo = event_topology.build(self.path)
        self.assertEqual(topo["nodes"], ["a", "b", "c"])
        self.assertEqual(topo["edges"], [("b", "a"), ("c", "b")])
        self.assertEqual(topo["roots"], ["a"])
        self.assertEqual(topo["leaves"], ["c"])
        self.assertTrue(topo["cycle_free"])

    def test_diamond(self):
        _write_log(self.path, [
            self._event("root"),
            self._event("l", {"parent": "root"}),
            self._event("r", {"parent": "root"}),
            self._event("merge", {"depends_on": ["l", "r"]}),
        ])
        topo = event_topology.build(self.path)
        self.assertEqual(topo["nodes"], ["l", "merge", "r", "root"])
        self.assertEqual(set(topo["edges"]),
                         {("l", "root"), ("r", "root"), ("merge", "l"), ("merge", "r")})
        self.assertEqual(topo["roots"], ["root"])
        self.assertEqual(topo["leaves"], ["merge"])
        self.assertTrue(topo["cycle_free"])

    def test_fork_and_join(self):
        _write_log(self.path, [
            self._event("a"),
            self._event("b", {"parent": "a"}),
            self._event("c", {"parent": "a"}),
            self._event("d", {"depends_on": ["b", "c"]}),
        ])
        topo = event_topology.build(self.path)
        self.assertEqual(topo["roots"], ["a"])
        self.assertEqual(topo["leaves"], ["d"])
        self.assertTrue(topo["cycle_free"])

    def test_self_loop_cycle(self):
        _write_log(self.path, [self._event("a", {"parent": "a"})])
        topo = event_topology.build(self.path)
        self.assertEqual(topo["edges"], [("a", "a")])
        self.assertFalse(topo["cycle_free"])

    def test_multi_node_cycle(self):
        _write_log(self.path, [
            self._event("a", {"parent": "b"}),
            self._event("b", {"parent": "c"}),
            self._event("c", {"parent": "a"}),
        ])
        topo = event_topology.build(self.path)
        self.assertFalse(topo["cycle_free"])
        self.assertEqual(topo["roots"], [])
        self.assertEqual(topo["leaves"], [])

    def test_depends_on_list(self):
        _write_log(self.path, [
            self._event("a"),
            self._event("b"),
            self._event("c", {"depends_on": ["a", "b"]}),
        ])
        topo = event_topology.build(self.path)
        self.assertEqual(set(topo["edges"]), {("c", "a"), ("c", "b")})
        self.assertEqual(topo["roots"], ["a", "b"])
        self.assertEqual(topo["leaves"], ["c"])
        self.assertTrue(topo["cycle_free"])

    def test_missing_file_raises(self):
        missing = os.path.join(self.tmp, "nope.jsonl")
        with self.assertRaises(FileNotFoundError):
            event_topology.build(missing)

    def test_malformed_lines_skipped(self):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(self._event("a")) + "\n")
            fh.write("this is not json\n")
            fh.write(json.dumps(self._event("b", {"parent": "a"})) + "\n")
        topo = event_topology.build(self.path)
        self.assertEqual(topo["nodes"], ["a", "b"])
        self.assertEqual(topo["edges"], [("b", "a")])

    def test_determinism(self):
        _write_log(self.path, [
            self._event("c", {"parent": "a"}),
            self._event("a"),
            self._event("b", {"depends_on": ["a", "c"]}),
        ])
        first = event_topology.build(self.path)
        second = event_topology.build(self.path)
        self.assertEqual(first, second)

    def test_read_only_source_unchanged(self):
        _write_log(self.path, [
            self._event("a"),
            self._event("b", {"parent": "a"}),
        ])
        with open(self.path, "r", encoding="utf-8") as fh:
            before = fh.read()
        event_topology.build(self.path)
        with open(self.path, "r", encoding="utf-8") as fh:
            after = fh.read()
        self.assertEqual(before, after)

    def test_dependency_to_unknown_node(self):
        _write_log(self.path, [self._event("b", {"parent": "ghost"})])
        topo = event_topology.build(self.path)
        self.assertEqual(set(topo["nodes"]), {"b", "ghost"})
        self.assertEqual(topo["edges"], [("b", "ghost")])
        # ghost is referenced but has no known dependencies -> it is a root
        self.assertEqual(topo["roots"], ["ghost"])
        self.assertEqual(topo["leaves"], ["b"])


if __name__ == "__main__":
    unittest.main()

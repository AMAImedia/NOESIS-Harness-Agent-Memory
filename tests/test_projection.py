"""Tests for event store projection, effect IDs, and crash tolerance."""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from noesis_harness import EventStore


class _Tmp(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="noesis_proj_")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class TestProjection(_Tmp):
    def test_multiple_reducers(self):
        es = EventStore(os.path.join(self.dir, "e.jsonl"))
        es.register_reducer("add", lambda s, p: (s or 0) + p["n"])
        es.register_reducer("mul", lambda s, p: (s or 0) * p["n"])
        es.append("add", {"n": 5})
        es.append("mul", {"n": 3})
        es.append("add", {"n": 2})
        self.assertEqual(es.project(0), 17)  # ((0+5)*3)+2

    def test_project_chain_helper(self):
        from noesis_harness.event_store import project_chain
        run = project_chain({"inc": lambda s, p: (s or 0) + p["n"]})
        events = [
            {"type": "inc", "payload": {"n": 1}},
            {"type": "inc", "payload": {"n": 2}},
            {"type": "other", "payload": {}},  # no reducer -> ignored
        ]
        self.assertEqual(run(events, 0), 3)


class TestEffectId(_Tmp):
    def test_chain_by_effect(self):
        es = EventStore(os.path.join(self.dir, "e.jsonl"))
        effect = "cycle-1:candidate-42:reply-1"
        es.append("candidate_found", {"effect_id": effect, "candidate": 42})
        es.append("reply_sent", {"effect_id": effect})
        es.append("candidate_found", {"effect_id": "cycle-1:candidate-7", "candidate": 7})
        chain = [ev for ev in es.iter_events() if ev["payload"].get("effect_id") == effect]
        self.assertEqual(len(chain), 2)


class TestCrashTolerance(_Tmp):
    def test_corrupt_tail_line_tolerated(self):
        p = os.path.join(self.dir, "e.jsonl")
        es = EventStore(p)
        es.append("a", {"v": 1})
        # Simulate a partial write: append garbage to the log tail
        with open(p, "a", encoding="utf-8") as fh:
            fh.write('{"event_id": "truncated", "type": "a", "pay\n')
        es2 = EventStore(p)  # reopen - must not crash on the corrupt line
        self.assertGreaterEqual(es2.count(), 1)

    def test_missing_file_ok(self):
        es = EventStore(os.path.join(self.dir, "nope.jsonl"))
        self.assertEqual(es.count(), 0)
        self.assertEqual(es.project(0), 0)


class TestSeq(_Tmp):
    def test_seq_monotonic(self):
        es = EventStore(os.path.join(self.dir, "e.jsonl"))
        id1 = es.append("a", {"i": 1})
        id2 = es.append("a", {"i": 2})
        recs = list(es.iter_events())
        self.assertEqual(recs[0]["seq"], 1)
        self.assertEqual(recs[1]["seq"], 2)
        self.assertNotEqual(id1, id2)

    def test_seq_survives_reopen(self):
        p = os.path.join(self.dir, "e.jsonl")
        es = EventStore(p)
        es.append("a", {"i": 1})
        es2 = EventStore(p)
        es2.append("a", {"i": 2})
        recs = list(es2.iter_events())
        self.assertEqual([r["seq"] for r in recs], [1, 2])


if __name__ == "__main__":
    unittest.main(verbosity=2)
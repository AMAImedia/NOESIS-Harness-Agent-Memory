"""Tests for mesh sync, inspect UI, and hybrid judge."""

import os
import shutil
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from noesis_harness import (
    Memory, Mesh, InspectUI, AgentTrace, HybridJudge, EventStore,
)


class _Tmp(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="noesis_mesh_")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class TestMesh(_Tmp):
    def test_push_pull(self):
        peers = os.path.join(self.dir, "peers")
        a = Memory(os.path.join(self.dir, "a.db"))
        b = Memory(os.path.join(self.dir, "b.db"))
        a.save("unique mesh fact about dubbing")
        Mesh(a, peers, node_id="a").push()
        n = Mesh(b, peers, node_id="b").pull()
        self.assertGreaterEqual(n, 1)
        self.assertTrue(any("dubbing" in h["fact"] for h in b.recall("dubbing")))


class TestInspect(_Tmp):
    def test_renders_html(self):
        m = Memory(os.path.join(self.dir, "m.db"))
        m.save("inspect me")
        es = EventStore(os.path.join(self.dir, "e.jsonl"))
        es.append("ping", {"ok": True})
        ui = InspectUI(m, es)
        self.assertIn("inspect me", ui.render_memories())
        self.assertIn("ping", ui.render_events())
        self.assertIn("memories", ui.render_index())


class TestTraceJudge(_Tmp):
    def test_trace_and_loop_fail(self):
        t = AgentTrace(os.path.join(self.dir, "t.jsonl"))
        t.record("out", {"text": "hi"})
        self.assertEqual(len(t.load()), 1)
        j = HybridJudge()
        bad = j.judge(["same", "same"])
        self.assertFalse(bad["pass"])
        self.assertIn("exact_loop", bad["reasons"])
        good = j.judge(["hello there"])
        self.assertTrue(good["pass"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

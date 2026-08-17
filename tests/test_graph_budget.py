"""Tests for graph, budget, HITL, scoped memory."""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from noesis_harness import Memory, MemoryGraph, Budget, HitlGate, ScopedMemory


class _Tmp(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="noesis_g_")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class TestGraph(_Tmp):
    def test_link_walk(self):
        g = MemoryGraph(os.path.join(self.dir, "g.db"))
        g.link("lead-1", "wants", "spanish-dub")
        g.link("spanish-dub", "lang", "es")
        w = g.walk("lead-1", depth=2)
        self.assertIn("es", w["nodes"])


class TestBudget(_Tmp):
    def test_no_spend_until_validated(self):
        b = Budget(os.path.join(self.dir, "b.db"), daily_cap=5)
        self.assertFalse(b.spend("k1", 1, validated=False)["ok"])
        self.assertTrue(b.spend("k1", 1, validated=True)["ok"])
        self.assertTrue(b.spend("k1", 1, validated=True)["idempotent"])
        self.assertEqual(b.remaining(), 4)


class TestHitl(_Tmp):
    def test_cannot_send_draft(self):
        h = HitlGate(os.path.join(self.dir, "h.db"))
        did = h.draft("hello")
        self.assertFalse(h.mark_sent(did)["ok"])
        self.assertTrue(h.approve(did)["ok"])
        self.assertTrue(h.mark_sent(did)["ok"])


class TestScope(_Tmp):
    def test_isolation(self):
        m = Memory(os.path.join(self.dir, "m.db"))
        a = ScopedMemory(m, "worker-a")
        b = ScopedMemory(m, "worker-b")
        a.save("secret pain point")
        self.assertTrue(a.recall("pain"))
        self.assertFalse(any("pain" in (x.get("fact") or "") for x in b.recall("pain")))


if __name__ == "__main__":
    unittest.main(verbosity=2)

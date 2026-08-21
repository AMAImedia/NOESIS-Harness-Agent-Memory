"""Tests for noesis_harness core primitives (stdlib unittest, no deps)."""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from noesis_harness import EventStore, Memory, Leases, Signals, Actions
from noesis_harness.event_store import EventStoreConflict


class _Tmp(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="noesis_test_")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class TestEventStore(_Tmp):
    def test_append_and_project(self):
        es = EventStore(os.path.join(self.dir, "events.jsonl"))
        es.register_reducer("inc", lambda s, p: (s or 0) + p["n"])
        es.append("inc", {"n": 1})
        es.append("inc", {"n": 2})
        self.assertEqual(es.project(0), 3)

    def test_idempotent_append(self):
        es = EventStore(os.path.join(self.dir, "e.jsonl"))
        a = es.append("x", {"v": 1}, event_id="fixed")
        b = es.append("x", {"v": 1}, event_id="fixed")
        self.assertEqual(a, b)
        self.assertEqual(es.count(), 1)

    def test_event_id_content_conflict_fails_closed(self):
        es = EventStore(os.path.join(self.dir, "e.jsonl"))
        es.append("x", {"v": 1}, event_id="fixed")
        with self.assertRaisesRegex(EventStoreConflict, "different content"):
            es.append("x", {"v": 2}, event_id="fixed")
        with open(es.path, "a", encoding="utf-8") as fh:
            fh.write('{"event_id":"fixed","type":"x","payload":{"v":99},"seq":2}\n')
        with self.assertRaises(EventStoreConflict):
            EventStore(es.path)

    def test_fingerprint_idempotency(self):
        es = EventStore(os.path.join(self.dir, "e.jsonl"))
        es.append("x", {"v": 1})
        es.append("x", {"v": 1})  # identical content, no event_id
        self.assertEqual(es.count(), 1)

    def test_replay_after_reopen(self):
        p = os.path.join(self.dir, "e.jsonl")
        es = EventStore(p)
        es.append("a", {"v": 1})
        es2 = EventStore(p)  # reopen -> _load_seen restores idempotency
        es2.append("a", {"v": 1})
        self.assertEqual(es2.count(), 1)


class TestMemory(_Tmp):
    def test_save_recall_dedup(self):
        m = Memory(os.path.join(self.dir, "mem.db"))
        i1 = m.save("client needs film dubbing in Spanish")
        i2 = m.save("client needs film dubbing in Spanish")  # dedup -> same id
        self.assertEqual(i1, i2)
        res = m.recall("dubbing")
        self.assertTrue(any("dubbing" in r["fact"] for r in res))

    def test_decay_bounded(self):
        m = Memory(os.path.join(self.dir, "mem.db"))
        m.save("some fact", confidence=0.9)
        for _ in range(10):
            m.decay()
        f = m.profile()[0]
        self.assertGreaterEqual(f["strength"], 0.09)

    def test_observe_summarize(self):
        m = Memory(os.path.join(self.dir, "mem.db"))
        m.observe("s1", "inbound", "hi")
        m.summarize("s1", "summary text")
        self.assertEqual(m.stats()["observations"], 1)
        self.assertEqual(m.stats()["summaries"], 1)

    def test_offload(self):
        m = Memory(os.path.join(self.dir, "mem.db"))
        m.offload("s9", "# big log\n" * 10, os.path.join(self.dir, "refs"))
        self.assertTrue(os.path.exists(os.path.join(self.dir, "refs", "s9.md")))


class TestLeases(_Tmp):
    def test_exclusive(self):
        L = Leases(os.path.join(self.dir, "l.db"), ttl=60)
        self.assertTrue(L.acquire("task1", "agentA")["ok"])
        self.assertFalse(L.acquire("task1", "agentB")["ok"])  # someone else holds
        self.assertTrue(L.acquire("task1", "agentA")["ok"])   # holder re-acquires

    def test_release_reclaim(self):
        L = Leases(os.path.join(self.dir, "l.db"), ttl=60)
        L.acquire("t", "A")
        self.assertTrue(L.release("t", "A"))
        self.assertTrue(L.acquire("t", "B")["ok"])

    def test_expiry_reclaim(self):
        L = Leases(os.path.join(self.dir, "l.db"), ttl=0)  # instant expiry
        L.acquire("t", "A")
        L.cleanup()
        self.assertTrue(L.acquire("t", "B")["ok"])


class TestSignals(_Tmp):
    def test_send_read_receipt(self):
        S = Signals(os.path.join(self.dir, "s.db"))
        S.send("director", "hello", to_agent="worker")
        inbox = S.read("worker")
        self.assertEqual(len(inbox), 1)
        self.assertEqual(len(S.read("worker")), 0)  # already read

    def test_broadcast_and_thread(self):
        S = Signals(os.path.join(self.dir, "s.db"))
        S.send("a", "to all")
        S.send("b", "reply", reply_to="")
        self.assertGreaterEqual(len(S.read("x")), 1)  # broadcast reaches any


class TestActions(_Tmp):
    def test_dependency_autounblock(self):
        A = Actions(os.path.join(self.dir, "a.db"))
        a = A.create("step1")
        b = A.create("step2", requires=[a])
        self.assertEqual(A.counts().get("blocked", 0), 1)
        A.complete(a)
        self.assertEqual(A.counts().get("blocked", 0), 0)
        self.assertEqual(A.counts().get("pending", 0), 1)

    def test_frontier_priority(self):
        A = Actions(os.path.join(self.dir, "a.db"))
        A.create("low", priority=1)
        A.create("high", priority=10)
        self.assertEqual(A.next()["title"], "high")


if __name__ == "__main__":
    unittest.main(verbosity=2)

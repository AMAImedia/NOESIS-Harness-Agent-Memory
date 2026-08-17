"""Tests for coordination edge cases: lease expiry, signal threads, DAG chains."""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from noesis_harness import Leases, Signals, Actions


class _Tmp(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="noesis_coord_")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class TestLeases(_Tmp):
    def test_holder_reacquire_ok(self):
        L = Leases(os.path.join(self.dir, "l.db"), ttl=60)
        self.assertTrue(L.acquire("t", "A")["ok"])
        r = L.acquire("t", "A")
        self.assertTrue(r["ok"])
        self.assertFalse(r["renewed"])  # same holder, no renewal

    def test_renew_only_holder(self):
        L = Leases(os.path.join(self.dir, "l.db"), ttl=60)
        L.acquire("t", "A")
        self.assertTrue(L.renew("t", "A"))
        self.assertFalse(L.renew("t", "B"))
        self.assertFalse(L.release("t", "B"))

    def test_cleanup_counts(self):
        L = Leases(os.path.join(self.dir, "l.db"), ttl=0)  # instant expiry
        L.acquire("t1", "A")
        L.acquire("t2", "A")
        n = L.cleanup()
        self.assertEqual(n, 2)

    def test_ttl_capped(self):
        L = Leases(os.path.join(self.dir, "l.db"), ttl=10_000)
        self.assertEqual(L.ttl, L.MAX_TTL)  # 3600 cap


class TestSignals(_Tmp):
    def test_thread_via_reply_to(self):
        S = Signals(os.path.join(self.dir, "s.db"))
        first = S.send("a", "start", to_agent="w")
        second = S.send("b", "reply", reply_to=first)
        threads = S.threads()
        self.assertEqual(len(threads), 1)  # both in one thread

    def test_expired_signal_not_read(self):
        S = Signals(os.path.join(self.dir, "s.db"), ttl=-1)  # instantly expired
        S.send("a", "old", to_agent="w")
        self.assertEqual(len(S.read("w")), 0)

    def test_cleanup_removes_expired(self):
        S = Signals(os.path.join(self.dir, "s.db"), ttl=-1)
        S.send("a", "old", to_agent="w")
        self.assertGreaterEqual(S.cleanup(), 1)


class TestActions(_Tmp):
    def test_multi_dependency_chain(self):
        A = Actions(os.path.join(self.dir, "a.db"))
        a = A.create("step1")
        b = A.create("step2", requires=[a])
        c = A.create("step3", requires=[a, b])
        self.assertEqual(A.counts().get("blocked", 0), 2)
        A.complete(a)
        # b unblocks; c still blocked (needs a AND b)
        self.assertEqual(A.counts().get("blocked", 0), 1)
        self.assertEqual(A.counts().get("pending", 0), 1)
        A.complete(b)
        self.assertEqual(A.counts().get("blocked", 0), 0)
        self.assertEqual(A.counts().get("pending", 0), 1)

    def test_claim_exclusive(self):
        A = Actions(os.path.join(self.dir, "a.db"))
        a = A.create("task")
        self.assertTrue(A.claim(a, "worker-1"))
        self.assertFalse(A.claim(a, "worker-2"))
        self.assertFalse(A.claim(a, "worker-1"))  # already active

    def test_complete_idempotent(self):
        A = Actions(os.path.join(self.dir, "a.db"))
        a = A.create("task")
        A.complete(a)
        A.complete(a)  # no-op, no crash
        self.assertEqual(A.counts()["done"], 1)

    def test_frontier_ordering(self):
        A = Actions(os.path.join(self.dir, "a.db"))
        A.create("low", priority=1)
        A.create("high", priority=10)
        A.create("mid", priority=5)
        frontier = A.frontier(2)
        self.assertEqual([f["title"] for f in frontier], ["high", "mid"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
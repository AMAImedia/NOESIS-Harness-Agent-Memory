"""Tests for DurableQueue and LoopGuard."""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from noesis_harness import DurableQueue, LoopGuard


class TestQueue(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="noesis_q_")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_dedup_lease_ack_recover(self):
        q = DurableQueue(os.path.join(self.dir, "q.db"), max_attempts=2)
        a = q.enqueue({"job": "x"})
        self.assertEqual(a, q.enqueue({"job": "x"}))
        leased = q.lease("w1")
        self.assertEqual(len(leased), 1)
        self.assertEqual(q.recover(), 1)
        self.assertEqual(q.fail(leased[0]["id"]), "pending")
        again = q.lease("w2")
        self.assertEqual(len(again), 1)
        self.assertEqual(q.fail(again[0]["id"]), "dead")
        q2 = DurableQueue(os.path.join(self.dir, "q2.db"))
        tid = q2.enqueue({"job": "y"})
        q2.ack(q2.lease("w")[0]["id"])
        self.assertEqual(q2.stats().get("done"), 1)
        self.assertEqual(tid, tid)


class TestLoopGuard(unittest.TestCase):
    def test_invalid_bounds_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "loop_guard_window_invalid"):
            LoopGuard(window=0)
        with self.assertRaisesRegex(ValueError, "loop_guard_window_invalid"):
            LoopGuard(window=True)
        with self.assertRaisesRegex(ValueError, "loop_guard_repeats_invalid"):
            LoopGuard(window=4, max_repeats=0)
        with self.assertRaisesRegex(ValueError, "loop_guard_repeats_invalid"):
            LoopGuard(window=2, max_repeats=3)

    def test_mapping_fingerprint_is_key_order_independent(self):
        self.assertEqual(LoopGuard.fingerprint({"b": 2, "a": 1}), LoopGuard.fingerprint({"a": 1, "b": 2}))

    def test_blocks_third_repeat(self):
        g = LoopGuard(window=8, max_repeats=2)
        self.assertTrue(g.check("ping")["ok"])
        self.assertTrue(g.check("ping")["ok"])
        self.assertFalse(g.check("ping")["ok"])
        self.assertTrue(g.check("pong")["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Tests for noesis_harness.leader_lease."""

from __future__ import annotations

import os
import tempfile
import threading
import time
import unittest

from noesis_harness.leader_lease import (
    KeyedQueue,
    LeaderLease,
    LeaseError,
    Sweeper,
)


class TestLeaderLease(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = os.path.join(self._tmp.name, "leader.json")

    def _lease(self):
        return LeaderLease(self.path)

    def test_acquire_free_lease(self):
        lease = self._lease()
        self.assertTrue(lease.try_acquire("alpha", ttl=10.0, now=0.0))
        self.assertEqual(lease.holder(0.0), "alpha")
        self.assertTrue(lease.is_leader("alpha", 0.0))

    def test_second_holder_blocked(self):
        lease = self._lease()
        self.assertTrue(lease.try_acquire("alpha", ttl=10.0, now=0.0))
        self.assertFalse(lease.try_acquire("beta", ttl=10.0, now=1.0))
        self.assertEqual(lease.holder(1.0), "alpha")

    def test_same_holder_reacquires_and_extends(self):
        lease = self._lease()
        self.assertTrue(lease.try_acquire("alpha", ttl=5.0, now=0.0))
        self.assertTrue(lease.try_acquire("alpha", ttl=5.0, now=3.0))
        self.assertEqual(lease.holder(4.0), "alpha")

    def test_expiry_allows_takeover(self):
        lease = self._lease()
        self.assertTrue(lease.try_acquire("alpha", ttl=5.0, now=0.0))
        self.assertFalse(lease.try_acquire("beta", ttl=5.0, now=4.999))
        self.assertTrue(lease.try_acquire("beta", ttl=5.0, now=5.0))
        self.assertEqual(lease.holder(5.0), "beta")

    def test_renew_by_non_holder_returns_false(self):
        lease = self._lease()
        self.assertTrue(lease.try_acquire("alpha", ttl=10.0, now=0.0))
        self.assertFalse(lease.renew("beta", ttl=10.0, now=1.0))
        self.assertEqual(lease.holder(1.0), "alpha")

    def test_renew_by_expired_holder_returns_false(self):
        lease = self._lease()
        self.assertTrue(lease.try_acquire("alpha", ttl=5.0, now=0.0))
        self.assertFalse(lease.renew("alpha", ttl=5.0, now=6.0))

    def test_renew_by_holder_succeeds(self):
        lease = self._lease()
        self.assertTrue(lease.try_acquire("alpha", ttl=5.0, now=0.0))
        self.assertTrue(lease.renew("alpha", ttl=5.0, now=4.0))
        self.assertEqual(lease.holder(8.0), "alpha")

    def test_release_by_holder(self):
        lease = self._lease()
        self.assertTrue(lease.try_acquire("alpha", ttl=10.0, now=0.0))
        self.assertTrue(lease.release("alpha"))
        self.assertIsNone(lease.holder(0.0))
        self.assertFalse(lease.is_leader("alpha", 0.0))

    def test_release_by_non_holder_returns_false(self):
        lease = self._lease()
        self.assertTrue(lease.try_acquire("alpha", ttl=10.0, now=0.0))
        self.assertFalse(lease.release("beta"))
        self.assertEqual(lease.holder(0.0), "alpha")

    def test_holder_returns_none_when_expired(self):
        lease = self._lease()
        self.assertTrue(lease.try_acquire("alpha", ttl=5.0, now=0.0))
        self.assertIsNone(lease.holder(5.0))
        self.assertIsNone(lease.holder(100.0))

    def test_fence_increments_per_acquire_and_is_stable(self):
        lease = self._lease()
        self.assertEqual(lease.fence(), 0)
        self.assertTrue(lease.try_acquire("alpha", ttl=5.0, now=0.0))
        self.assertEqual(lease.fence(), 1)
        self.assertTrue(lease.renew("alpha", ttl=5.0, now=1.0))
        self.assertEqual(lease.fence(), 1)
        self.assertTrue(lease.try_acquire("beta", ttl=5.0, now=6.0))
        self.assertEqual(lease.fence(), 2)
        self.assertTrue(lease.release("beta"))
        self.assertEqual(lease.fence(), 2)
        self.assertTrue(lease.try_acquire("gamma", ttl=5.0, now=6.5))
        self.assertEqual(lease.fence(), 3)

    def test_persistence_across_two_instances(self):
        first = LeaderLease(self.path)
        self.assertTrue(first.try_acquire("alpha", ttl=10.0, now=0.0))
        fence = first.fence()
        second = LeaderLease(self.path)
        self.assertTrue(second.is_leader("alpha", 5.0))
        self.assertEqual(second.holder(5.0), "alpha")
        self.assertEqual(second.fence(), fence)
        self.assertFalse(second.try_acquire("beta", ttl=10.0, now=5.0))

    def test_determinism_with_injected_now(self):
        run_a = self._replay("replay-a.json")
        run_b = self._replay("replay-b.json")
        self.assertEqual(run_a, run_b)

    def _replay(self, name):
        lease = LeaderLease(os.path.join(self._tmp.name, name))
        trace = []
        trace.append(lease.try_acquire("alpha", ttl=2.0, now=0.0))
        trace.append(lease.holder(1.0))
        trace.append(lease.renew("alpha", ttl=2.0, now=1.5))
        trace.append(lease.holder(3.0))
        trace.append(lease.try_acquire("beta", ttl=2.0, now=2.0))
        trace.append(lease.fence())
        trace.append(lease.release("beta"))
        trace.append(lease.holder(2.5))
        return trace

    def test_corrupt_lease_file_raises(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("{not valid json")
        lease = self._lease()
        with self.assertRaises(LeaseError):
            lease.holder(0.0)


class TestKeyedQueue(unittest.TestCase):

    def test_serializes_same_key_in_order(self):
        queue = KeyedQueue()
        order = []
        barrier = threading.Barrier(4)

        def make(tag):
            def fn():
                order.append(("start", tag))
                time.sleep(0.02)
                order.append(("end", tag))
                return tag
            return fn

        def worker(tag):
            barrier.wait()
            queue.submit("shared", make(tag))

        threads = [
            threading.Thread(target=worker, args=(tag,))
            for tag in ("a", "b", "c")
        ]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join(timeout=5.0)

        self.assertEqual(len(order), 6)
        for index in range(0, 6, 2):
            start = order[index]
            end = order[index + 1]
            self.assertEqual(start[0], "start")
            self.assertEqual(end[0], "end")
            self.assertEqual(start[1], end[1])

    def test_parallelizes_different_keys(self):
        queue = KeyedQueue()
        barrier = threading.Barrier(2, timeout=5.0)

        def fn():
            barrier.wait()
            return "ok"

        results = {}

        def worker(key):
            results[key] = queue.submit(key, fn)

        threads = [
            threading.Thread(target=worker, args=(key,))
            for key in ("left", "right")
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5.0)

        self.assertEqual(results, {"left": "ok", "right": "ok"})

    def test_exception_propagates_after_release(self):
        queue = KeyedQueue()

        def boom():
            raise RuntimeError("kaboom")

        with self.assertRaises(RuntimeError):
            queue.submit("key", boom)
        self.assertEqual(queue.submit("key", lambda: 7), 7)

    def test_returns_value_deterministically(self):
        queue = KeyedQueue()
        self.assertEqual(queue.submit("k", lambda: "value"), "value")


class TestSweeper(unittest.TestCase):

    def test_first_run_then_skip_within_interval_then_run_after(self):
        sweeper = Sweeper(interval=5.0)
        calls = []

        def fn():
            calls.append("tick")
            return len(calls)

        first = sweeper.run_once(fn, now=100.0)
        self.assertTrue(first["ran"])
        self.assertEqual(first["at"], 100.0)
        self.assertEqual(first["result"], 1)
        self.assertEqual(sweeper.last_run(), 100.0)

        skipped = sweeper.run_once(fn, now=104.0)
        self.assertFalse(skipped["ran"])
        self.assertEqual(skipped["at"], 104.0)
        self.assertEqual(sweeper.last_run(), 100.0)

        third = sweeper.run_once(fn, now=105.0)
        self.assertTrue(third["ran"])
        self.assertEqual(sweeper.last_run(), 105.0)
        self.assertEqual(len(calls), 2)

    def test_error_is_captured_without_advancing_last_run(self):
        sweeper = Sweeper(interval=5.0)

        def boom():
            raise ValueError("sweep failed")

        result = sweeper.run_once(boom, now=10.0)
        self.assertFalse(result["ran"])
        self.assertEqual(result["at"], 10.0)
        self.assertIsInstance(result["error"], ValueError)
        self.assertIsNone(sweeper.last_run())

        retry = sweeper.run_once(boom, now=11.0)
        self.assertFalse(retry["ran"])
        self.assertIn("error", retry)
        self.assertIsNone(sweeper.last_run())

    def test_skipped_tick_never_raises_and_does_not_call(self):
        sweeper = Sweeper(interval=10.0)
        calls = []

        def fn():
            calls.append("ran")
            return "done"

        self.assertTrue(sweeper.run_once(fn, now=0.0)["ran"])
        for offset in (1.0, 5.0, 9.999):
            tick = sweeper.run_once(fn, now=offset)
            self.assertFalse(tick["ran"])
        self.assertEqual(len(calls), 1)

    def test_sweeper_determinism_with_injected_now(self):
        first = self._replay()
        second = self._replay()
        self.assertEqual(first, second)

    def _replay(self):
        sweeper = Sweeper(interval=3.0)
        trace = []
        for now in (0.0, 1.0, 3.0, 4.0, 6.0):
            trace.append(sweeper.run_once(lambda: "tick", now=now)["ran"])
        trace.append(sweeper.last_run())
        return trace


if __name__ == "__main__":
    unittest.main()

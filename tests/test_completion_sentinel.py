import os
import tempfile
import unittest
from pathlib import Path

from noesis_harness.completion_sentinel import (
    DONE_SUFFIX,
    LEASE_SUFFIX,
    READY_SUFFIX,
    RESULT_SUFFIX,
    ResourceLease,
    SentinelTimeout,
    StepMarker,
    TurnSentinel,
)


class _Clock:
    """Deterministic clock advanced only by explicit sleep calls."""

    def __init__(self, step: float = 0.05) -> None:
        self.t = 0.0
        self.step = step

    def now(self) -> float:
        return self.t

    def sleep(self, dt: float) -> None:
        self.t += max(dt, self.step)


class NullClock:
    """Clock that fails loudly if it is ever asked to sleep."""

    def now(self) -> float:
        return 0.0

    def sleep(self, dt: float) -> None:
        raise AssertionError("sleep must not be called")


class CompletionSentinelTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def test_mark_done_is_done_and_read_result(self):
        sentinel = TurnSentinel(self.root)
        self.assertFalse(sentinel.is_done("s1", 0))
        path = sentinel.mark_done("s1", 0, "payload")
        self.assertTrue(sentinel.is_done("s1", 0))
        self.assertEqual(sentinel.read_result("s1", 0), "payload")
        self.assertTrue(os.path.exists(path))
        self.assertTrue(os.path.exists(sentinel.paths("s1", 0)["done"]))

    def test_duplicate_identical_mark_done_is_noop(self):
        sentinel = TurnSentinel(self.root)
        first = sentinel.mark_done("s1", 0, "payload")
        done_path = sentinel.paths("s1", 0)["done"]
        before = os.path.getmtime(done_path)
        second = sentinel.mark_done("s1", 0, "payload")
        self.assertEqual(first, second)
        self.assertEqual(os.path.getmtime(done_path), before)
        self.assertEqual(sentinel.read_result("s1", 0), "payload")

    def test_conflicting_result_raises_value_error(self):
        sentinel = TurnSentinel(self.root)
        sentinel.mark_done("s1", 0, "first")
        with self.assertRaises(ValueError):
            sentinel.mark_done("s1", 0, "second")
        self.assertEqual(sentinel.read_result("s1", 0), "first")

    def test_wait_for_done_returns_immediately_when_already_done(self):
        sentinel = TurnSentinel(self.root)
        sentinel.mark_done("s1", 7, "ready-payload")
        result = sentinel.wait_for_done(
            "s1", 7, timeout=1.0, now=NullClock().now, sleep=NullClock().sleep
        )
        self.assertEqual(result, "ready-payload")

    def test_wait_for_done_returns_result_after_polling(self):
        sentinel = TurnSentinel(self.root)
        clock = _Clock(step=0.05)
        calls = {"n": 0}

        original = sentinel.is_done

        def delayed(session, turn):
            calls["n"] += 1
            if calls["n"] >= 3:
                sentinel.mark_done(session, turn, "late")
            return original(session, turn)

        sentinel.is_done = delayed  # type: ignore[assignment]
        result = sentinel.wait_for_done(
            "s1", 0, timeout=5.0, now=clock.now, sleep=clock.sleep
        )
        self.assertEqual(result, "late")

    def test_wait_for_done_timeout_carries_last_lines(self):
        sentinel = TurnSentinel(self.root)
        clock = _Clock(step=0.05)
        diagnostics = []

        def last_lines(result_path):
            diagnostics.append(result_path)
            return ["stdout: still working", "stderr: none"]

        with self.assertRaises(SentinelTimeout) as ctx:
            sentinel.wait_for_done(
                "s1",
                3,
                timeout=0.25,
                now=clock.now,
                sleep=clock.sleep,
                last_lines=last_lines,
            )
        error = ctx.exception
        self.assertEqual(error.session, "s1")
        self.assertEqual(error.turn, 3)
        self.assertEqual(error.last_lines, ["stdout: still working", "stderr: none"])
        self.assertIn("s1", str(error))
        self.assertIn("3", str(error))
        self.assertIn("timeout", str(error))
        self.assertEqual(len(diagnostics), 1)
        self.assertGreaterEqual(clock.t, 0.25)

    def test_sentinels_are_isolated_per_turn(self):
        sentinel = TurnSentinel(self.root)
        sentinel.mark_done("s1", 1, "one")
        self.assertTrue(sentinel.is_done("s1", 1))
        self.assertFalse(sentinel.is_done("s1", 2))
        self.assertIsNone(sentinel.read_result("s1", 2))
        sentinel.mark_done("s1", 2, "two")
        self.assertEqual(sentinel.read_result("s1", 1), "one")
        self.assertEqual(sentinel.read_result("s1", 2), "two")

    def test_sentinels_are_isolated_per_session(self):
        sentinel = TurnSentinel(self.root)
        sentinel.mark_done("alpha", 0, "a")
        self.assertFalse(sentinel.is_done("beta", 0))
        sentinel.mark_done("beta", 0, "b")
        self.assertEqual(sentinel.read_result("alpha", 0), "a")
        self.assertEqual(sentinel.read_result("beta", 0), "b")

    def test_pending_turns_reports_asymmetric_state(self):
        sentinel = TurnSentinel(self.root)
        sentinel.mark_done("s1", 1, "complete")
        result_only = sentinel.paths("s1", 2)["result"]
        with open(result_only, "w", encoding="utf-8") as handle:
            handle.write("orphan-result")
        done_only = sentinel.paths("s1", 3)["done"]
        with open(done_only, "w", encoding="utf-8") as handle:
            handle.write("done\n")
        self.assertEqual(sentinel.pending_turns("s1"), [2, 3])
        self.assertEqual(sentinel.pending_turns("s2"), [])

    def test_suffix_constants(self):
        self.assertEqual(DONE_SUFFIX, ".done")
        self.assertEqual(RESULT_SUFFIX, ".result")
        self.assertEqual(READY_SUFFIX, ".ready")
        self.assertEqual(LEASE_SUFFIX, ".lease")

    def test_mark_ready_and_is_ready(self):
        marker = StepMarker(self.root)
        self.assertFalse(marker.is_ready("compile"))
        path = marker.mark_ready("compile", "ok")
        self.assertTrue(marker.is_ready("compile"))
        self.assertTrue(path.endswith(READY_SUFFIX))
        with open(path, "r", encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "ok")
        marker.mark_ready("compile", "different")
        with open(path, "r", encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "ok")

    def test_run_once_runs_then_skips(self):
        marker = StepMarker(self.root)
        calls = {"n": 0}

        def action():
            calls["n"] += 1
            return "detail-%d" % calls["n"]

        first = marker.run_once("step", action)
        second = marker.run_once("step", action)
        self.assertEqual(first, {"ran": True, "detail": "detail-1"})
        self.assertEqual(second, {"ran": False, "detail": "detail-1"})
        self.assertEqual(calls["n"], 1)

    def test_run_once_does_not_mark_ready_on_exception(self):
        marker = StepMarker(self.root)

        def boom():
            raise RuntimeError("action failed")

        with self.assertRaises(RuntimeError):
            marker.run_once("step", boom)
        self.assertFalse(marker.is_ready("step"))

        def recover():
            return "recovered"

        outcome = marker.run_once("step", recover)
        self.assertEqual(outcome, {"ran": True, "detail": "recovered"})
        self.assertTrue(marker.is_ready("step"))

    def test_lease_acquire_and_holder(self):
        lease = ResourceLease(self.root)
        lease_id = lease.acquire("gpu", "worker-a")
        self.assertEqual(lease_id, ResourceLease.lease_id("gpu", "worker-a"))
        self.assertEqual(len(lease_id), 16)
        self.assertEqual(lease.holder("gpu"), "worker-a")
        self.assertTrue(os.path.exists(os.path.join(self.root, "gpu" + LEASE_SUFFIX)))

    def test_second_holder_cannot_acquire(self):
        lease = ResourceLease(self.root)
        lease.acquire("gpu", "worker-a")
        with self.assertRaises(RuntimeError):
            lease.acquire("gpu", "worker-b")
        self.assertEqual(lease.holder("gpu"), "worker-a")
        again = lease.acquire("gpu", "worker-a")
        self.assertEqual(again, ResourceLease.lease_id("gpu", "worker-a"))

    def test_ttl_expiry_allows_new_holder(self):
        lease = ResourceLease(self.root)
        clock = _Clock(step=1.0)
        lease.acquire("gpu", "worker-a", now=clock.now, ttl_seconds=10.0)
        with self.assertRaises(RuntimeError):
            lease.acquire("gpu", "worker-b", now=clock.now)
        clock.t = 100.0
        self.assertIsNone(lease.holder("gpu", now=clock.now))
        lease_id = lease.acquire("gpu", "worker-b", now=clock.now)
        self.assertEqual(lease_id, ResourceLease.lease_id("gpu", "worker-b"))
        self.assertEqual(lease.holder("gpu", now=clock.now), "worker-b")

    def test_only_holder_can_release(self):
        lease = ResourceLease(self.root)
        lease.acquire("gpu", "worker-a")
        self.assertFalse(lease.release("gpu", "worker-b"))
        self.assertEqual(lease.holder("gpu"), "worker-a")
        self.assertTrue(lease.release("gpu", "worker-a"))
        self.assertIsNone(lease.holder("gpu"))
        self.assertFalse(lease.release("gpu", "worker-a"))

    def test_lease_id_is_deterministic(self):
        self.assertEqual(
            ResourceLease.lease_id("gpu", "worker-a"),
            ResourceLease.lease_id("gpu", "worker-a"),
        )
        self.assertNotEqual(
            ResourceLease.lease_id("gpu", "worker-a"),
            ResourceLease.lease_id("gpu", "worker-b"),
        )
        other_root = tempfile.mkdtemp()
        other = ResourceLease(other_root)
        first = ResourceLease(self.root).acquire("gpu", "worker-a")
        second = other.acquire("gpu", "worker-a")
        self.assertEqual(first, second)
        self.assertEqual(len(first), 16)


if __name__ == "__main__":
    unittest.main()

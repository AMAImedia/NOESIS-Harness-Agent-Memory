"""Tests for fork isolation scheduling (noesis_harness.fork_isolation)."""

import unittest

from noesis_harness.fork_isolation import (
    CacheSafeSnapshot,
    ChildScope,
    ForkCoordinator,
    ForkError,
    Status,
    canonical_digest,
)


def make_snapshot(**overrides):
    base = {
        "system_prompt": "SYS",
        "user_context": "USER",
        "system_context": "CTX",
        "tool_keys": ("read", "write"),
        "messages_digest": canonical_digest([{"role": "user", "content": "hi"}]),
    }
    base.update(overrides)
    return CacheSafeSnapshot(**base)


class ForkIsolationTests(unittest.TestCase):
    def setUp(self):
        self.coord = ForkCoordinator()
        self.snapshot = make_snapshot()

    def test_fork_creates_isolated_child(self):
        scope = self.coord.fork(None, self.snapshot, lambda s: "ok")
        self.assertIsInstance(scope, ChildScope)
        self.assertIsNone(scope.parent_id)
        self.assertEqual(scope.agent_id, "fork-1")
        self.assertEqual(self.coord.children(), ["fork-1"])

    def test_child_cannot_write_unshared_state(self):
        def run(scope):
            with self.assertRaises(ForkError):
                scope.set_state("private", 1)
            return "ok"

        self.coord.fork(None, self.snapshot, run, share=("shared",))

    def test_child_can_write_shared_state(self):
        def run(scope):
            scope.set_state("shared", 42)
            self.assertEqual(scope.get_state("shared"), 42)
            return scope.get_state("shared")

        scope = self.coord.fork(None, self.snapshot, run, share=("shared",))
        self.assertEqual(scope.result, 42)
        self.assertEqual(scope.get_state("shared"), 42)

    def test_child_clones_parent_state_and_inherits_shared(self):
        child = self.coord.fork(
            None, self.snapshot, lambda s: s.set_state("a", 7) or "done", share=("a",)
        )
        grand = self.coord.fork(
            child.agent_id, self.snapshot, lambda s: s.get_state("a")
        )
        self.assertEqual(grand.result, 7)

    def test_complete_is_terminal_and_blocks_writes(self):
        def run(scope):
            scope.set_state("a", 1)
            scope.complete("done")
            scope.complete("again")
            self.assertTrue(scope.is_terminal())
            self.assertEqual(scope.status, Status.COMPLETED)
            self.assertEqual(scope.result, "done")
            with self.assertRaises(ForkError):
                scope.set_state("a", 2)
            return "ignored"

        scope = self.coord.fork(None, self.snapshot, run, share=("a",))
        self.assertEqual(scope.status, Status.COMPLETED)
        self.assertEqual(scope.result, "done")

    def test_fail_sets_failed_status(self):
        def run(scope):
            scope.fail("boom")
            return "ignored"

        scope = self.coord.fork(None, self.snapshot, run)
        self.assertEqual(scope.status, Status.FAILED)
        self.assertEqual(scope.error, "boom")
        self.assertTrue(scope.is_terminal())

    def test_cancel_sets_cancelled_status(self):
        def run(scope):
            scope.cancel()
            return "ignored"

        scope = self.coord.fork(None, self.snapshot, run)
        self.assertEqual(scope.status, Status.CANCELLED)
        self.assertTrue(scope.is_terminal())

    def test_cache_safe_second_fork_same_snapshot_allowed(self):
        first = self.coord.fork(None, self.snapshot, lambda s: "a")
        second = self.coord.fork(None, self.snapshot, lambda s: "b")
        self.assertEqual(first.result, "a")
        self.assertEqual(second.result, "b")
        self.assertEqual(self.coord.children(), ["fork-1", "fork-2"])

    def test_cache_unsafe_fork_different_snapshot_raises(self):
        self.coord.fork(None, self.snapshot, lambda s: "a")
        changed = make_snapshot(system_prompt="CHANGED")
        with self.assertRaises(ForkError):
            self.coord.fork(None, changed, lambda s: "b")

    def test_register_parent_conflict_raises(self):
        child = self.coord.fork(None, self.snapshot, lambda s: "a")
        self.coord.register_parent(child.agent_id, self.snapshot)
        with self.assertRaises(ForkError):
            self.coord.register_parent(child.agent_id, make_snapshot(system_prompt="X"))

    def test_children_listing_is_sorted_per_parent(self):
        root = self.coord.fork(None, self.snapshot, lambda s: "root")
        self.coord.fork(root.agent_id, self.snapshot, lambda s: "c2")
        self.coord.fork(root.agent_id, self.snapshot, lambda s: "c1")
        self.assertEqual(self.coord.children(root.agent_id), ["fork-2", "fork-3"])
        self.assertEqual(self.coord.children(), ["fork-1"])

    def test_cascade_cancel_descendants_leaves_no_orphans(self):
        def spawn(scope):
            self.coord.fork(scope.agent_id, self.snapshot, lambda s: "leaf")
            return scope.agent_id

        root = self.coord.fork(None, self.snapshot, lambda s: "root")
        branch = self.coord.fork(root.agent_id, self.snapshot, spawn)
        sibling = self.coord.fork(root.agent_id, self.snapshot, lambda s: "sibling")
        leaf = self.coord.children(branch.agent_id)[0]
        expected = sorted([root.agent_id, branch.agent_id, leaf, sibling.agent_id])
        cancelled = self.coord.cancel_subtree(root.agent_id)
        self.assertEqual(cancelled, expected)
        for agent_id in expected:
            self.assertEqual(
                self.coord.result_channel(agent_id)["status"], Status.CANCELLED
            )

    def test_non_cascade_cancel_only_cancels_node(self):
        root = self.coord.fork(None, self.snapshot, lambda s: "root")
        branch = self.coord.fork(root.agent_id, self.snapshot, lambda s: "b")
        sibling = self.coord.fork(root.agent_id, self.snapshot, lambda s: "s")
        cancelled = self.coord.cancel_subtree(branch.agent_id, cascade=False)
        self.assertEqual(cancelled, [branch.agent_id])
        self.assertEqual(
            self.coord.result_channel(branch.agent_id)["status"], Status.CANCELLED
        )
        self.assertEqual(
            self.coord.result_channel(sibling.agent_id)["status"], Status.COMPLETED
        )

    def test_result_channel_is_one_way_and_hides_state(self):
        def run(scope):
            scope.set_state("a", "secret")
            return {"answer": 1}

        scope = self.coord.fork(None, self.snapshot, run, share=("a",))
        envelope = self.coord.result_channel(scope.agent_id)
        self.assertEqual(
            sorted(envelope.keys()), ["agent_id", "error", "result", "status"]
        )
        self.assertNotIn("_state", envelope)
        self.assertNotIn("secret", repr(envelope))
        self.assertEqual(envelope["agent_id"], scope.agent_id)
        self.assertEqual(envelope["status"], Status.COMPLETED)
        self.assertEqual(envelope["result"], {"answer": 1})
        self.assertIsNone(envelope["error"])

    def test_result_channel_unknown_agent_raises(self):
        with self.assertRaises(ForkError):
            self.coord.result_channel("missing")

    def test_canonical_digest_is_order_independent(self):
        left = {"a": 1, "b": {"x": 2, "y": [3, 4]}}
        right = {"b": {"y": [3, 4], "x": 2}, "a": 1}
        self.assertEqual(canonical_digest(left), canonical_digest(right))
        self.assertTrue(canonical_digest(left).startswith("sha256:"))
        self.assertNotEqual(canonical_digest(left), canonical_digest({"a": 1}))

    def test_snapshot_from_messages_is_byte_stable(self):
        first = CacheSafeSnapshot.from_messages(
            "S", "U", "C", ["b", "a"],
            [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "yo"}],
        )
        second = CacheSafeSnapshot.from_messages(
            "S", "U", "C", ("b", "a"),
            [{"content": "hi", "role": "user"}, {"content": "yo", "role": "assistant"}],
        )
        expected_messages = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "yo"},
        ]
        self.assertEqual(first, second)
        self.assertEqual(first.messages_digest, canonical_digest(expected_messages))

    def test_callback_exception_is_captured_as_failed(self):
        def run(scope):
            raise ValueError("nope")

        scope = self.coord.fork(None, self.snapshot, run)
        self.assertEqual(scope.status, Status.FAILED)
        self.assertIn("ValueError", scope.error)
        self.assertIn("nope", scope.error)

    def test_fork_rejects_unknown_parent(self):
        with self.assertRaises(ForkError):
            self.coord.fork("missing", self.snapshot, lambda s: "x")

    def test_determinism_across_coordinators(self):
        def sequence(coord):
            root = coord.fork(None, make_snapshot(), lambda s: "root")
            coord.fork(root.agent_id, make_snapshot(), lambda s: "child")
            return coord.children(), coord.result_channel(root.agent_id)

        ids_a, env_a = sequence(ForkCoordinator())
        ids_b, env_b = sequence(ForkCoordinator())
        self.assertEqual(ids_a, ids_b)
        self.assertEqual(env_a, env_b)
        self.assertEqual(ids_a, ["fork-1"])


if __name__ == "__main__":
    unittest.main()

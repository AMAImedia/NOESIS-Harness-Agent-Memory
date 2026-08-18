import os
import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path

from noesis_harness.coordination import Actions, Leases
from noesis_harness.parallel_agent import AgentLane, ParallelExecutionError, SafeParallelExecutor


class SafeParallelExecutorTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="noesis_parallel_")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_parallel_lanes_have_unique_workspaces_and_provenance(self):
        executor = SafeParallelExecutor(self.root, max_concurrency=2)
        seen = []
        lock = threading.Lock()

        def callback(ctx):
            target = ctx.path("result.txt")
            target.write_text(ctx.agent_id, encoding="utf-8")
            with lock:
                seen.append((ctx.agent_id, ctx.task_id, ctx.session_id, str(ctx.workspace)))
            time.sleep(0.02)
            return target.read_text(encoding="utf-8")

        lanes = [
            AgentLane("agent-a", "task-a", "agent-a", ("read", "workspace_write", "provenance"), True, True),
            AgentLane("agent-b", "task-b", "agent-b", ("read", "workspace_write", "provenance"), True, True),
        ]
        results = executor.execute(lanes, callback, session_id="session-1", approval=True)
        self.assertEqual([r.status for r in results], ["passed", "passed"])
        self.assertEqual({r.agent_id for r in results}, {"agent-a", "agent-b"})
        self.assertEqual({r.task_id for r in results}, {"task-a", "task-b"})
        self.assertEqual({r.workspace for r in results}, {str(Path(self.root) / "agent-a"), str(Path(self.root) / "agent-b")})
        self.assertTrue(all(row[2] == "session-1" for row in seen))
        self.assertNotEqual(seen[0][3], seen[1][3])

    def test_bound_is_capped(self):
        self.assertEqual(SafeParallelExecutor(self.root, max_concurrency=100).max_concurrency, 8)
        self.assertEqual(SafeParallelExecutor(self.root, max_concurrency=0).max_concurrency, 1)

    def test_denies_unsafe_capabilities_before_start(self):
        executor = SafeParallelExecutor(self.root)
        with self.assertRaisesRegex(ParallelExecutionError, "capability_denied:credentials"):
            executor.execute([AgentLane("a", "t", "a", ("read", "credentials"))], lambda _: None)
        self.assertEqual(executor.audit, [])

    def test_requires_approval_for_writes(self):
        executor = SafeParallelExecutor(self.root)
        lane = AgentLane("a", "t", "a", ("read", "workspace_write"), True, False)
        with self.assertRaisesRegex(ParallelExecutionError, "approval_required:a"):
            executor.execute([lane], lambda _: None, approval=False)
        self.assertEqual(executor.audit, [])

    def test_rejects_duplicate_or_outside_workspaces(self):
        executor = SafeParallelExecutor(self.root)
        with self.assertRaisesRegex(ParallelExecutionError, "workspace_not_unique"):
            executor.execute([AgentLane("a", "t1", "same"), AgentLane("b", "t2", "same")], lambda _: None)
        with self.assertRaisesRegex(ParallelExecutionError, "workspace_outside_root"):
            executor.execute([AgentLane("a", "t1", "../escape")], lambda _: None)

    def test_path_rejects_traversal(self):
        executor = SafeParallelExecutor(self.root)
        results = executor.execute([AgentLane("a", "t1", "a")], lambda ctx: ctx.path("../escape"))
        self.assertEqual(results[0].status, "failed")
        self.assertIn("workspace_escape", results[0].error)
        self.assertFalse(os.path.exists(os.path.join(self.root, "escape")))

    def test_actions_ledger_completes_success_and_requeues_failure(self):
        actions = Actions(os.path.join(self.root, "actions.db"))
        success_id = actions.create("success")
        failure_id = actions.create("failure")
        executor = SafeParallelExecutor(self.root)

        def callback(ctx):
            if ctx.task_id == failure_id:
                raise RuntimeError("interrupted")
            return "verified-result"

        lanes = [AgentLane("agent-a", success_id, "success"), AgentLane("agent-b", failure_id, "failure")]
        results = executor.execute(lanes, callback, action_store=actions)
        by_task = {r.task_id: r for r in results}
        self.assertEqual(by_task[success_id].status, "passed")
        self.assertEqual(by_task[failure_id].status, "failed")
        self.assertEqual(actions.counts().get("done"), 1)
        self.assertEqual(actions.counts().get("pending"), 1)
        self.assertTrue(actions.claim(failure_id, "recovery-agent"))

    def test_actions_ledger_denial_does_not_run_callback(self):
        actions = Actions(os.path.join(self.root, "actions.db"))
        action_id = actions.create("already-owned")
        self.assertTrue(actions.claim(action_id, "other-agent"))
        executor = SafeParallelExecutor(self.root)
        called = []
        results = executor.execute([AgentLane("agent-a", action_id, "already-owned")], lambda _: called.append(True), action_store=actions)
        self.assertEqual(results[0].status, "blocked")
        self.assertEqual(results[0].error, "action_not_claimed")
        self.assertEqual(called, [])

    def test_ttl_lease_blocks_held_lane_and_releases_completed_lane(self):
        leases = Leases(os.path.join(self.root, "leases.db"), ttl=60)
        leases.acquire("held-task", "other-agent")
        executor = SafeParallelExecutor(self.root)
        called = []

        def callback(ctx):
            called.append(ctx.task_id)
            return "done"

        lanes = [AgentLane("agent-a", "held-task", "held"), AgentLane("agent-b", "free-task", "free")]
        results = executor.execute(lanes, callback, lease_store=leases)
        by_task = {r.task_id: r for r in results}
        self.assertEqual(by_task["held-task"].status, "blocked")
        self.assertEqual(by_task["free-task"].status, "passed")
        self.assertEqual(called, ["free-task"])
        self.assertTrue(leases.acquire("free-task", "another-agent")["ok"])

    def test_one_failed_lane_does_not_cancel_other_lane(self):
        executor = SafeParallelExecutor(self.root, max_concurrency=2)

        def callback(ctx):
            if ctx.agent_id == "bad":
                raise RuntimeError("expected")
            return "good"

        lanes = [AgentLane("bad", "task-bad", "bad"), AgentLane("good", "task-good", "good")]
        results = executor.execute(lanes, callback)
        by_agent = {r.agent_id: r for r in results}
        self.assertEqual(by_agent["bad"].status, "failed")
        self.assertEqual(by_agent["good"].status, "passed")
        self.assertEqual(by_agent["bad"].error, "RuntimeError: expected")
        self.assertEqual(sorted(e["event"] for e in executor.audit), sorted(["lane_started", "lane_started", "lane_completed", "lane_failed"]))

    def test_cooperative_cancellation_isolated_and_reported(self):
        from noesis_harness.parallel_agent import CancellationToken
        token = CancellationToken()
        executor = SafeParallelExecutor(self.root)

        def callback(ctx):
            token.cancel("operator_stop")
            ctx.check_cancelled()

        result = executor.execute([AgentLane("a", "cancel-task", "cancel")], callback, cancellation=token)[0]
        self.assertEqual(result.status, "cancelled")
        self.assertIn("operator_stop", result.error)
        self.assertIn("lane_cancelled", [event["event"] for event in executor.audit])

    def test_deadline_cancellation_is_reported(self):
        executor = SafeParallelExecutor(self.root)
        result = executor.execute([AgentLane("a", "deadline-task", "deadline")], lambda ctx: ctx.check_cancelled(), max_duration_seconds=0.000001)[0]
        self.assertEqual(result.status, "cancelled")
        self.assertIn("deadline_exceeded", result.error)


if __name__ == "__main__":
    unittest.main(verbosity=2)

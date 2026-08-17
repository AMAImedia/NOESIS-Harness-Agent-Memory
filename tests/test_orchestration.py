import tempfile
import unittest
from pathlib import Path

from noesis_harness.orchestration import WorkCoordinator


class OrchestrationTests(unittest.TestCase):
    def test_only_one_agent_claims_a_task(self):
        with tempfile.TemporaryDirectory() as d:
            c=WorkCoordinator(str(Path(d)/"work.db"))
            c.add("a", scope="research")
            first=c.claim("agent-1", scopes=("research",), ttl=100, now=10)
            second=c.claim("agent-2", scopes=("research",), ttl=100, now=10)
            self.assertIsNotNone(first)
            self.assertIsNone(second)
            self.assertEqual(c.status("a")["owner"], "agent-1")

    def test_dependencies_and_completion_unblock_child(self):
        with tempfile.TemporaryDirectory() as d:
            c=WorkCoordinator(str(Path(d)/"work.db"))
            c.add("parent")
            c.add("child", deps=("parent",))
            claim=c.claim("agent", now=1)
            self.assertEqual(claim.task_id, "parent")
            self.assertTrue(c.complete("parent", "agent", {"ok":True}))
            child=c.claim("agent-2", now=2)
            self.assertEqual(child.task_id, "child")

    def test_expired_lease_reclaims_and_duplicate_completion_is_denied(self):
        with tempfile.TemporaryDirectory() as d:
            c=WorkCoordinator(str(Path(d)/"work.db"))
            c.add("a")
            claim=c.claim("agent-1", ttl=1, now=10)
            self.assertEqual(c.reclaim_expired(now=12), 1)
            new_claim=c.claim("agent-2", ttl=10, now=12)
            self.assertEqual(new_claim.attempt, 2)
            self.assertTrue(c.complete("a", "agent-2", "done"))
            self.assertFalse(c.complete("a", "agent-2", "again"))


if __name__ == "__main__": unittest.main()


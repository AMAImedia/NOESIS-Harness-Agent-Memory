import tempfile
import unittest

from noesis_harness.learning_promotion import LearningPromotionPipeline
from noesis_harness.promotion_integration import EvaluatorRegistry, PromotionIntegration
from noesis_harness.health_server import HealthServer


class PromotionIntegrationTests(unittest.TestCase):
    def integration(self):
        pipe = LearningPromotionPipeline(tempfile.mkdtemp(), b"integration-promotion-key")
        registry = EvaluatorRegistry()
        registry.register("eval-1", lambda receipt: [{"case_id": "holdout-a", "passed": True}])
        return PromotionIntegration(pipe, registry=registry)

    def test_only_terminal_tasks_create_receipts(self):
        integration = self.integration()
        with self.assertRaisesRegex(ValueError, "task_not_terminal"):
            integration.capture_task_completion({"task_id": "task-1", "status": "active"}, payload={}, source_digest="src", policy_digest="pol", agent_id="agent", scope="project:demo")
        receipt = integration.capture_task_completion({"task_id": "task-1", "status": "done"}, payload={"result": "ok"}, source_digest="src", policy_digest="pol", agent_id="agent", scope="project:demo")
        self.assertEqual(receipt.experience_id, "task-1")

    def test_registry_and_review_only_flow_defaults_to_no_activation(self):
        integration = self.integration()
        receipt = integration.capture_task_completion({"task_id": "task-2", "status": "completed"}, payload={"result": "ok"}, source_digest="src", policy_digest="pol", agent_id="agent", scope="project:demo")
        evaluation = integration.evaluate(receipt.receipt_id, "eval-1")
        proposal = integration.propose(receipt.receipt_id, evaluation.evaluation_id, skill_name="reviewed-skill", content="# reviewed\n")
        integration.approve(proposal.proposal_id, approved_by="owner", tests=lambda: True)
        promoted, signature = integration.promote(proposal.proposal_id, content="# reviewed\n", verify=lambda path: path.is_file())
        self.assertEqual(promoted.state, "promoted")
        self.assertEqual(integration.pipeline.active_version("reviewed-skill"), "")
        self.assertTrue(signature)
        snapshot = integration.snapshot()
        self.assertFalse(snapshot["automatic_activation"])
        self.assertEqual(snapshot["counts"]["promotion_completed"], 1)

    def test_registry_duplicate_and_unknown_versions_fail_closed(self):
        integration = self.integration()
        with self.assertRaisesRegex(ValueError, "invalid_or_duplicate"):
            integration.registry.register("eval-1", lambda _: [])
        with self.assertRaisesRegex(KeyError, "evaluator_not_registered"):
            integration.registry.get("missing")

    def test_health_server_exposes_bounded_promotion_snapshot(self):
        integration = self.integration()
        integration.telemetry.record("promotion_proposed", proposal_id="p1", content="must-not-leak")
        server = HealthServer(promotion_telemetry=integration.telemetry)
        snapshot = server.telemetry_snapshot()
        self.assertIn("learning_promotion", snapshot)
        self.assertFalse(snapshot["learning_promotion"]["automatic_activation"])
        self.assertEqual(snapshot["learning_promotion"]["events"][0]["content"], "[REDACTED]")

    def test_telemetry_redacts_content_like_fields(self):
        integration = self.integration()
        integration.telemetry.record("test", content="secret skill", api_key="token")
        snapshot = integration.snapshot()
        self.assertEqual(snapshot["events"][0]["content"], "[REDACTED]")
        self.assertEqual(snapshot["events"][0]["api_key"], "[REDACTED]")


if __name__ == "__main__":
    unittest.main()

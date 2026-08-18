import tempfile
import unittest

from noesis_harness.learning_promotion import LearningPromotionPipeline
from noesis_harness.promotion_integration import EvaluatorRegistry, OwnershipPolicySimulator, PolicySimulation, PromotionApprovalAction, PromotionEventBridge, PromotionIntegration
from noesis_harness.task_session_api import TaskSessionStore
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

    def test_event_bridge_replays_terminal_tasks_once_and_keeps_activation_disabled(self):
        integration = self.integration()
        task_store = TaskSessionStore(tempfile.mktemp())
        session = task_store.create_session("owner", session_id="session-bridge")
        task_store.create_task(session.session_id, "learn", "owner", task_id="task-bridge")
        task_store.transition_task("task-bridge", "planned")
        task_store.transition_task("task-bridge", "executing")
        task_store.transition_task("task-bridge", "review")
        task_store.transition_task("task-bridge", "committed")
        checkpoint = tempfile.mktemp()
        bridge = PromotionEventBridge(integration, checkpoint)
        calls = []

        def policy(task):
            calls.append(task["task_id"])
            return PolicySimulation(True, "source", "policy", "agent", "project:demo", {"result": "ok"})

        first = bridge.poll(task_store, policy)
        second = PromotionEventBridge(integration, checkpoint).poll(task_store, policy)
        self.assertEqual(first[0]["status"], "completed")
        self.assertEqual(second, ())
        self.assertEqual(calls, ["task-bridge"])
        self.assertEqual(len(integration.pipeline._receipts), 1)
        self.assertFalse(integration.snapshot()["automatic_activation"])

    def test_event_bridge_denies_policy_and_malformed_simulation_fail_closed(self):
        integration = self.integration()
        task_store = TaskSessionStore(tempfile.mktemp())
        session = task_store.create_session("owner", session_id="session-deny")
        task_store.create_task(session.session_id, "blocked", "owner", task_id="task-deny")
        task_store.transition_task("task-deny", "planned")
        task_store.transition_task("task-deny", "executing")
        task_store.transition_task("task-deny", "failed")
        checkpoint = tempfile.mktemp()
        bridge = PromotionEventBridge(integration, checkpoint)
        denied = bridge.poll(task_store, lambda _: {"allowed": False, "reason": "scope_not_approved"})
        self.assertEqual(denied[0]["status"], "denied")
        self.assertEqual(len(integration.pipeline._receipts), 0)
        self.assertEqual(bridge.poll(task_store, lambda _: {"allowed": True}), ())
        self.assertEqual(integration.snapshot()["counts"]["promotion_blocked"], 1)

    def test_event_bridge_rejects_malformed_simulation_and_cancelled_tasks(self):
        integration = self.integration()
        task_store = TaskSessionStore(tempfile.mktemp())
        session = task_store.create_session("owner", session_id="session-malformed")
        task_store.create_task(session.session_id, "malformed", "owner", task_id="task-malformed")
        task_store.transition_task("task-malformed", "planned")
        task_store.transition_task("task-malformed", "executing")
        task_store.transition_task("task-malformed", "failed")
        task_store.create_task(session.session_id, "cancelled", "owner", task_id="task-cancelled")
        task_store.transition_task("task-cancelled", "cancelled")
        bridge = PromotionEventBridge(integration, tempfile.mktemp())
        outcomes = bridge.poll(task_store, lambda task: {"allowed": True} if task["task_id"] == "task-malformed" else {"allowed": False})
        self.assertEqual([item["status"] for item in outcomes], ["denied", "denied"])
        self.assertIn("policy_simulation_error:ValueError", outcomes[0]["reason"])
        self.assertEqual(outcomes[1]["reason"], "cancelled_task")
        self.assertEqual(len(integration.pipeline._receipts), 0)

    def test_ownership_policy_uses_authoritative_session_and_owner_metadata(self):
        task_store = TaskSessionStore(tempfile.mktemp())
        session = task_store.create_session("owner", session_id="session-owner")
        task_store.create_task(session.session_id, "owned", "creator", task_id="task-owned")
        task_store.transition_task("task-owned", "planned")
        task_store.transition_task("task-owned", "executing")
        task_store.transition_task("task-owned", "review")
        task_store.transition_task("task-owned", "committed")
        simulator = OwnershipPolicySimulator(task_store, lambda task_id: "agent-authoritative", allowed_scopes=("session:session-owner",))
        event = {"task_id": "task-owned", "session_id": "session-owner", "state": "committed", "reason": "review_approved"}
        result = simulator.simulate(event)
        self.assertTrue(result.allowed)
        self.assertEqual(result.agent_id, "agent-authoritative")
        self.assertEqual(result.scope, "session:session-owner")
        mismatch = simulator.simulate({**event, "session_id": "other-session"})
        self.assertFalse(mismatch.allowed)
        self.assertEqual(mismatch.reason, "ownership_session_mismatch")
        missing = OwnershipPolicySimulator(task_store, lambda _: "", allowed_scopes=()).simulate(event)
        self.assertFalse(missing.allowed)
        self.assertEqual(missing.reason, "task_owner_missing")

    def _proposal(self, integration, task_id="task-action"):
        receipt = integration.capture_task_completion({"task_id": task_id, "status": "completed"}, payload={"result": "ok"}, source_digest="src", policy_digest="pol", agent_id="agent-owner", scope="project:demo")
        evaluation = integration.evaluate(receipt.receipt_id, "eval-1")
        return integration.propose(receipt.receipt_id, evaluation.evaluation_id, skill_name="skill-" + task_id, content="# skill\n")

    def test_operator_action_executor_approves_with_signed_idempotent_receipt(self):
        from noesis_harness.promotion_integration import PromotionActionExecutor
        integration = self.integration()
        proposal = self._proposal(integration)
        executor = PromotionActionExecutor(integration, tempfile.mktemp(), approval_tests=lambda: True)
        action = PromotionApprovalAction("action-approve", "approve", proposal.proposal_id, "independent-reviewer")
        first = executor.handle(action)
        replay = executor.handle(action)
        self.assertEqual(first["status"], "applied")
        self.assertEqual(replay["status"], "replayed")
        receipt = first["receipt"]
        self.assertEqual(receipt["new_state"], "approved")
        signature_payload = {key: receipt[key] for key in ("action_id", "proposal_id", "action", "operator_id", "previous_state", "new_state")}
        self.assertTrue(integration.pipeline.verify_signature(signature_payload, receipt["signed_receipt"]))
        self.assertEqual(integration.pipeline._proposals[proposal.proposal_id].state, "approved")
        self.assertEqual(integration.pipeline.active_version(proposal.skill_name), "")

    def test_operator_action_executor_rejects_self_review_and_supports_reject(self):
        from noesis_harness.promotion_integration import PromotionActionExecutor
        integration = self.integration()
        proposal = self._proposal(integration, "task-reject")
        executor = PromotionActionExecutor(integration, tempfile.mktemp())
        with self.assertRaisesRegex(PermissionError, "independent_reviewer_required"):
            executor.handle(PromotionApprovalAction("action-self", "approve", proposal.proposal_id, "agent-owner"))
        rejected = executor.handle(PromotionApprovalAction("action-reject", "reject", proposal.proposal_id, "independent-reviewer"))
        self.assertEqual(rejected["receipt"]["new_state"], "rejected")

    def test_operator_action_executor_rolls_back_only_explicitly_promoted_proposal(self):
        from noesis_harness.promotion_integration import PromotionActionExecutor
        integration = self.integration()
        proposal = self._proposal(integration, "task-rollback")
        executor = PromotionActionExecutor(integration, tempfile.mktemp())
        executor.handle(PromotionApprovalAction("action-approve-r", "approve", proposal.proposal_id, "independent-reviewer"))
        promoted, _ = integration.promote(proposal.proposal_id, content="# skill\n", verify=lambda path: path.is_file(), activate=False)
        self.assertEqual(promoted.state, "promoted")
        rolled = executor.handle(PromotionApprovalAction("action-rollback", "rollback", proposal.proposal_id, "independent-reviewer", expected_state="promoted"))
        self.assertEqual(rolled["receipt"]["new_state"], "rolled_back")
        self.assertEqual(integration.pipeline.active_version(proposal.skill_name), "")

    def test_promotion_approval_action_is_versioned_and_non_secret(self):
        action = PromotionApprovalAction.from_mapping({"schema_version": "noesis.promotion-approval.v1", "action_id": "action-1", "action": "approve", "proposal_id": "proposal-1", "operator_id": "operator-1"})
        self.assertEqual(action.to_mapping()["action"], "approve")
        with self.assertRaisesRegex(ValueError, "unsupported_approval_action"):
            PromotionApprovalAction.from_mapping({"schema_version": "noesis.promotion-approval.v1", "action_id": "a", "action": "promote", "proposal_id": "p", "operator_id": "o"})
        with self.assertRaisesRegex(ValueError, "unsupported_approval_action_schema"):
            PromotionApprovalAction.from_mapping({"schema_version": "wrong", "action_id": "a", "action": "approve", "proposal_id": "p", "operator_id": "o"})

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
